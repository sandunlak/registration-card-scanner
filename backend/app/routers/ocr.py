"""Project-scoped OCR jobs and recognition-result endpoints."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_session
from app.core.exceptions import NotFoundError, OCRUnavailableError, ValidationError
from app.models.image import ImageAsset
from app.models.ocr import OcrJob, OcrResult
from app.models.project import Project
from app.schemas.ocr import (
    HandwritingRegion,
    OcrJobRead,
    OcrResultRead,
    OcrResultsRead,
    OcrStartRequest,
)
from app.services.image_storage import resolve_storage_key
from app.services.ocr_service import create_ocr_pipeline

router = APIRouter(tags=["ocr"])
logger = logging.getLogger(__name__)
_INFERENCE_LOCK = threading.Lock()


def _recognize_serially(pipeline, source_path, selections):
    with _INFERENCE_LOCK:
        return pipeline.recognize(source_path, selections)


async def _get_scoped_image(
    project_id: int, image_id: int, session: AsyncSession
) -> ImageAsset:
    if await session.get(Project, project_id) is None:
        raise NotFoundError(f"Project with ID {project_id} not found.")
    image = await session.get(ImageAsset, image_id)
    if image is None or image.project_id != project_id:
        raise NotFoundError(f"Image {image_id} not found in project {project_id}.")
    return image


async def _get_scoped_job(
    project_id: int, image_id: int, job_id: int, session: AsyncSession
) -> OcrJob:
    await _get_scoped_image(project_id, image_id, session)
    job = await session.get(OcrJob, job_id)
    if job is None or job.project_id != project_id or job.image_id != image_id:
        raise NotFoundError(f"OCR job {job_id} not found for this image and project.")
    return job


async def _job_read(job: OcrJob, session: AsyncSession) -> OcrJobRead:
    count = await session.exec(select(func.count(OcrResult.id)).where(OcrResult.job_id == job.id))
    return OcrJobRead(
        id=int(job.id),  # type: ignore[arg-type]
        project_id=job.project_id,
        image_id=job.image_id,
        status=job.status,  # type: ignore[arg-type]
        error_code=job.error_code,
        error_message=job.error_message,
        attempt_count=job.attempt_count,
        duration_ms=job.duration_ms,
        result_count=count.one(),
        requested_at=job.requested_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def _queue_job(
    image: ImageAsset,
    data: OcrStartRequest,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
) -> OcrJobRead:
    existing_result = await session.exec(select(OcrJob).where(OcrJob.image_id == image.id))
    existing = existing_result.first()
    if existing is not None:
        return await _job_read(existing, session)

    job = OcrJob(
        project_id=image.project_id,
        image_id=int(image.id),  # type: ignore[arg-type]
        status="queued",
        handwriting_regions=[region.model_dump() for region in data.handwriting_regions],
    )
    session.add(job)
    try:
        await session.commit()
        await session.refresh(job)
    except IntegrityError:
        await session.rollback()
        existing_result = await session.exec(select(OcrJob).where(OcrJob.image_id == image.id))
        existing = existing_result.first()
        if existing is None:
            raise
        return await _job_read(existing, session)
    background_tasks.add_task(process_ocr_job, int(job.id))  # type: ignore[arg-type]
    return await _job_read(job, session)


@router.post(
    "/{project_id}/images/{image_id}/ocr",
    response_model=OcrJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_ocr(
    project_id: int,
    image_id: int,
    background_tasks: BackgroundTasks,
    data: OcrStartRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> OcrJobRead:
    """Start printed/general OCR and optionally recognize selected handwriting lines."""
    image = await _get_scoped_image(project_id, image_id, session)
    if image.status != "ready":
        raise ValidationError("Wait for image preprocessing to finish before starting OCR.")
    request = data or OcrStartRequest()
    if len(request.handwriting_regions) > settings.ocr_max_handwriting_regions:
        raise ValidationError(
            f"A maximum of {settings.ocr_max_handwriting_regions} handwriting crops is allowed."
        )
    return await _queue_job(image, request, session, background_tasks)


@router.get(
    "/{project_id}/images/{image_id}/ocr",
    response_model=OcrJobRead | None,
)
async def get_image_ocr_job(
    project_id: int,
    image_id: int,
    session: AsyncSession = Depends(get_session),
) -> OcrJobRead | None:
    """Return the single OCR job, or null if OCR has not been started."""
    await _get_scoped_image(project_id, image_id, session)
    result = await session.exec(select(OcrJob).where(OcrJob.image_id == image_id))
    job = result.first()
    if job is None:
        return None
    if job.project_id != project_id:
        raise NotFoundError("No OCR job exists for this image.")
    return await _job_read(job, session)


@router.get(
    "/{project_id}/images/{image_id}/ocr/{job_id}",
    response_model=OcrJobRead,
)
async def get_ocr_job(
    project_id: int,
    image_id: int,
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> OcrJobRead:
    """Check the status of an OCR job after verifying project and image ownership."""
    return await _job_read(await _get_scoped_job(project_id, image_id, job_id, session), session)


@router.get(
    "/{project_id}/images/{image_id}/ocr/{job_id}/results",
    response_model=OcrResultsRead,
)
async def get_ocr_results(
    project_id: int,
    image_id: int,
    job_id: int,
    session: AsyncSession = Depends(get_session),
) -> OcrResultsRead:
    """Retrieve region text, coordinates, model IDs, and only model-provided confidence."""
    job = await _get_scoped_job(project_id, image_id, job_id, session)
    results = await session.exec(
        select(OcrResult)
        .where(OcrResult.job_id == job_id, OcrResult.project_id == project_id)
        .order_by(OcrResult.region_index)
    )
    return OcrResultsRead(
        job=await _job_read(job, session),
        items=[OcrResultRead.model_validate(item) for item in results.all()],
    )


@router.post(
    "/{project_id}/images/{image_id}/ocr/{job_id}/retry",
    response_model=OcrJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_ocr(
    project_id: int,
    image_id: int,
    job_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> OcrJobRead:
    """Retry a failed job in place, preserving its ID and avoiding duplicate OCR jobs."""
    job = await _get_scoped_job(project_id, image_id, job_id, session)
    if job.status != "failed":
        raise ValidationError("Only a failed OCR job can be retried.")
    job.status = "queued"
    job.error_code = None
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.duration_ms = None
    job.attempt_count += 1
    job.requested_at = datetime.now(timezone.utc)
    session.add(job)
    old_results = await session.exec(select(OcrResult).where(OcrResult.job_id == job_id))
    for old_result in old_results.all():
        await session.delete(old_result)
    await session.commit()
    await session.refresh(job)
    background_tasks.add_task(process_ocr_job, int(job.id))  # type: ignore[arg-type]
    return await _job_read(job, session)


async def process_ocr_job(job_id: int) -> None:
    """Run OCR off the request thread and persist only recognition output, never fields."""
    async with AsyncSessionLocal() as session:
        job = await session.get(OcrJob, job_id)
        if job is None or job.status != "queued":
            return
        image = await session.get(ImageAsset, job.image_id)
        if image is None or image.project_id != job.project_id:
            await _mark_failed(session, job, "image_unavailable", "The source image is unavailable.")
            return

        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        job.error_code = None
        job.error_message = None
        session.add(job)
        await session.commit()

        started = time.perf_counter()
        try:
            source_key = image.processed_key or image.original_key
            source_path = resolve_storage_key(source_key)
            if not source_path.is_file():
                raise ValidationError("The processed image file is missing from local storage.")
            selections = [HandwritingRegion.model_validate(item) for item in job.handwriting_regions]
            pipeline = await run_in_threadpool(create_ocr_pipeline)
            regions, width, height = await run_in_threadpool(
                _recognize_serially, pipeline, source_path, selections
            )
            for index, region in enumerate(regions):
                session.add(
                    OcrResult(
                        project_id=job.project_id,
                        image_id=job.image_id,
                        job_id=job_id,
                        region_index=index,
                        text=region.text,
                        polygon=region.polygon,
                        coordinate_space="processed",
                        image_width=width,
                        image_height=height,
                        recognition_type=region.recognition_type,
                        model_id=region.model_id,
                        model_version=region.model_version,
                        confidence=region.confidence,
                        extra_metadata=region.extra_metadata,
                    )
                )
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.duration_ms = int((time.perf_counter() - started) * 1000)
            session.add(job)
            await session.commit()
        except OCRUnavailableError as exc:
            await session.rollback()
            current = await session.get(OcrJob, job_id)
            if current is not None:
                await _mark_failed(session, current, "models_unavailable", exc.detail)
        except ValidationError as exc:
            await session.rollback()
            current = await session.get(OcrJob, job_id)
            if current is not None:
                await _mark_failed(session, current, "unreadable_image", exc.detail)
        except Exception as exc:
            await session.rollback()
            logger.error("OCR job %s failed (%s)", job_id, type(exc).__name__)
            current = await session.get(OcrJob, job_id)
            if current is not None:
                await _mark_failed(
                    session, current, "inference_failed", "OCR inference failed; retry or inspect server logs."
                )


async def _mark_failed(
    session: AsyncSession, job: OcrJob, error_code: str, error_message: str
) -> None:
    job.status = "failed"
    job.error_code = error_code
    job.error_message = error_message[:500]
    job.completed_at = datetime.now(timezone.utc)
    session.add(job)
    await session.commit()