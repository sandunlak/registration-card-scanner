"""Project-scoped image upload, preprocessing, preview, and deletion endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.exceptions import AppError, FileTooLargeError, NotFoundError, ValidationError
from app.models.image import ImageAsset
from app.models.project import Project, RegistrationRecord
from app.schemas.image import (
    ImageAdjust,
    ImageAssetRead,
    ImageBatchRead,
    ImageBatchUploadRead,
    ImageUploadFailure,
    ImageUploadOutcome,
)
from app.services.image_processing import process_image
from app.services.image_processing import ImageProcessingResult
from app.services.image_storage import (
    cleanup_empty_directories,
    delete_storage_keys,
    resolve_storage_key,
    write_image,
)

router = APIRouter(prefix="", tags=["images"])
CHUNK_SIZE = 64 * 1024


def _as_read(image: ImageAsset) -> ImageAssetRead:
    return ImageAssetRead(
        id=image.id,  # type: ignore[arg-type]
        project_id=image.project_id,
        record_id=image.record_id,
        status=image.status,  # type: ignore[arg-type]
        metadata=image.metadata_json,
        variants=list(image.variant_keys),
        rotation=image.rotation,  # type: ignore[arg-type]
        crop=image.crop,
        error_message=image.error_message,
        created_at=image.created_at,
        updated_at=image.updated_at,
    )


async def _get_project(project_id: int, session: AsyncSession) -> Project:
    project = await session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"Project with ID {project_id} not found.")
    return project


async def _get_image(project_id: int, image_id: int, session: AsyncSession) -> ImageAsset:
    image = await session.get(ImageAsset, image_id)
    if image is None or image.project_id != project_id:
        raise NotFoundError(f"Image {image_id} not found in project {project_id}.")
    return image


async def _read_bounded(file: UploadFile) -> bytes:
    maximum = settings.max_upload_size_mb * 1024 * 1024
    if maximum <= 0:
        raise FileTooLargeError("Image uploads are disabled by the configured size limit.")
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(min(CHUNK_SIZE, maximum - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > maximum:
            raise FileTooLargeError(f"Image exceeds the {settings.max_upload_size_mb} MB per-file limit.")
        chunks.append(chunk)
    return b"".join(chunks)


async def _process(content: bytes, filename: str, content_type: str | None, rotation: int = 0,
                   crop: dict[str, float] | None = None) -> ImageProcessingResult:
    return await run_in_threadpool(
        process_image,
        content,
        filename,
        content_type,
        max_pixels=settings.max_image_pixels,
        rotation=rotation,
        crop=crop,
    )


def _store_outputs(
    project_id: int, record_id: int, result: ImageProcessingResult
) -> tuple[str, dict[str, str], list[str]]:
    created: list[str] = []
    try:
        processed_key = write_image(project_id, record_id, "processed", ".jpg", result.processed)
        created.append(processed_key)
        variant_keys: dict[str, str] = {}
        for name, content in result.variants.items():
            extension = ".png" if name == "adaptive_threshold" else ".jpg"
            key = write_image(project_id, record_id, "variants", extension, content)
            created.append(key)
            variant_keys[name] = key
        return processed_key, variant_keys, created
    except Exception:
        delete_storage_keys(created)
        cleanup_empty_directories(project_id, record_id)
        raise


async def _create_image(project_id: int, upload: UploadFile, session: AsyncSession) -> ImageAssetRead:
    filename = upload.filename or ""
    content = await _read_bounded(upload)
    processed = await _process(content, filename, upload.content_type)
    record = RegistrationRecord(project_id=project_id, source_image_path=None, extracted_data={})
    session.add(record)
    created_keys: list[str] = []
    try:
        await session.flush()
        record_id = int(record.id)  # type: ignore[arg-type]
        extension = Path(filename).suffix.lower()
        original_key = write_image(project_id, record_id, "originals", extension, content)
        created_keys.append(original_key)
        processed_key, variant_keys, output_keys = _store_outputs(project_id, record_id, processed)
        created_keys.extend(output_keys)
        record.source_image_path = original_key
        image = ImageAsset(
            project_id=project_id,
            record_id=record_id,
            original_key=original_key,
            processed_key=processed_key,
            variant_keys=variant_keys,
            status="ready",
            metadata_json=processed.metadata,
        )
        session.add(image)
        await session.commit()
        await session.refresh(image)
        return _as_read(image)
    except Exception:
        await session.rollback()
        delete_storage_keys(created_keys)
        cleanup_empty_directories(project_id, int(record.id or 0))
        raise


async def _reprocess(image: ImageAsset, session: AsyncSession) -> ImageAssetRead:
    image.status = "processing"
    image.error_message = None
    session.add(image)
    await session.commit()
    await session.refresh(image)

    created_keys: list[str] = []
    try:
        original_path = resolve_storage_key(image.original_key)
        if not original_path.is_file():
            raise ValidationError("The original image file is missing from local storage.")
        content = await run_in_threadpool(original_path.read_bytes)
        processed = await _process(
            content,
            original_path.name,
            None,
            image.rotation,
            image.crop,
        )
        processed_key, variant_keys, created_keys = _store_outputs(
            image.project_id, image.record_id, processed
        )
        old_keys = [key for key in [image.processed_key, *image.variant_keys.values()] if key]
        image.processed_key = processed_key
        image.variant_keys = variant_keys
        image.metadata_json = processed.metadata
        image.status = "ready"
        image.error_message = None
        session.add(image)
        await session.commit()
        await session.refresh(image)
        delete_storage_keys(old_keys)
        return _as_read(image)
    except Exception as exc:
        await session.rollback()
        delete_storage_keys(created_keys)
        image = await session.get(ImageAsset, image.id)
        if image is None:
            raise NotFoundError("Image was removed while it was being processed.") from exc
        image.status = "failed"
        image.error_message = exc.detail if isinstance(exc, AppError) else "Image preprocessing failed."
        session.add(image)
        await session.commit()
        await session.refresh(image)
        return _as_read(image)


@router.post(
    "/{project_id}/images",
    response_model=ImageAssetRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(
    project_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ImageAssetRead:
    """Upload and preprocess one JPEG, PNG, or WebP image for a project."""
    await _get_project(project_id, session)
    return await _create_image(project_id, file, session)


@router.post(
    "/{project_id}/images/batch",
    response_model=ImageBatchUploadRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_images(
    project_id: int,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> ImageBatchUploadRead:
    """Upload a bounded batch; each result independently reports success or failure."""
    await _get_project(project_id, session)
    if not files:
        raise ValidationError("Select at least one image.")
    if len(files) > settings.max_images_per_batch:
        raise ValidationError(f"A batch may contain at most {settings.max_images_per_batch} images.")
    items: list[ImageUploadOutcome] = []
    for upload in files:
        try:
            items.append(ImageUploadOutcome(image=await _create_image(project_id, upload, session)))
        except AppError as exc:
            items.append(ImageUploadOutcome(failure=ImageUploadFailure(error_message=exc.detail)))
        except Exception:
            items.append(
                ImageUploadOutcome(
                    failure=ImageUploadFailure(error_message="Image upload could not be completed.")
                )
            )
    return ImageBatchUploadRead(items=items)


@router.get("/{project_id}/images", response_model=ImageBatchRead)
async def list_images(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> ImageBatchRead:
    """List image metadata for the specified project only."""
    await _get_project(project_id, session)
    result = await session.exec(
        select(ImageAsset)
        .where(ImageAsset.project_id == project_id)
        .order_by(ImageAsset.created_at.desc())
    )
    return ImageBatchRead(items=[_as_read(image) for image in result.all()])


@router.get("/{project_id}/images/{image_id}", response_model=ImageAssetRead)
async def get_image(
    project_id: int,
    image_id: int,
    session: AsyncSession = Depends(get_session),
) -> ImageAssetRead:
    """Retrieve processing state and non-sensitive image metadata."""
    await _get_project(project_id, session)
    return _as_read(await _get_image(project_id, image_id, session))


@router.get("/{project_id}/images/{image_id}/preview")
async def get_preview(
    project_id: int,
    image_id: int,
    variant: str = "processed",
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    """Serve a private original, processed image, or preprocessing variant."""
    await _get_project(project_id, session)
    image = await _get_image(project_id, image_id, session)
    keys = {"original": image.original_key, "processed": image.processed_key, **image.variant_keys}
    key = keys.get(variant)
    if key is None:
        raise NotFoundError(f"Preview variant '{variant}' is not available.")
    path = resolve_storage_key(key)
    if not path.is_file():
        raise NotFoundError("Image preview is not available in local storage.")
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.post("/{project_id}/images/{image_id}/retry", response_model=ImageAssetRead)
async def retry_preprocessing(
    project_id: int,
    image_id: int,
    session: AsyncSession = Depends(get_session),
) -> ImageAssetRead:
    """Retry preprocessing the stored original without creating another record."""
    await _get_project(project_id, session)
    return await _reprocess(await _get_image(project_id, image_id, session), session)


@router.post("/{project_id}/images/{image_id}/adjust", response_model=ImageAssetRead)
async def adjust_image(
    project_id: int,
    image_id: int,
    data: ImageAdjust,
    session: AsyncSession = Depends(get_session),
) -> ImageAssetRead:
    """Rotate and/or manually crop the image, always starting from the original."""
    await _get_project(project_id, session)
    image = await _get_image(project_id, image_id, session)
    image.rotation = data.rotation
    image.crop = data.crop
    session.add(image)
    await session.commit()
    await session.refresh(image)
    return await _reprocess(image, session)


@router.post("/{project_id}/images/{image_id}/replace", response_model=ImageAssetRead)
async def replace_image(
    project_id: int,
    image_id: int,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ImageAssetRead:
    """Replace source pixels while retaining the existing registration record."""
    await _get_project(project_id, session)
    image = await _get_image(project_id, image_id, session)
    content = await _read_bounded(file)
    processed = await _process(content, file.filename or "", file.content_type)
    created_keys: list[str] = []
    old_keys = [image.original_key, image.processed_key, *image.variant_keys.values()]
    try:
        extension = Path(file.filename or "").suffix.lower()
        original_key = write_image(project_id, image.record_id, "originals", extension, content)
        created_keys.append(original_key)
        processed_key, variants, output_keys = _store_outputs(project_id, image.record_id, processed)
        created_keys.extend(output_keys)
        image.original_key = original_key
        image.processed_key = processed_key
        image.variant_keys = variants
        image.metadata_json = processed.metadata
        image.status = "ready"
        image.error_message = None
        image.rotation = 0
        image.crop = None
        record = await session.get(RegistrationRecord, image.record_id)
        if record is not None:
            record.source_image_path = original_key
            session.add(record)
        session.add(image)
        await session.commit()
        await session.refresh(image)
        delete_storage_keys([key for key in old_keys if key])
        return _as_read(image)
    except Exception:
        await session.rollback()
        delete_storage_keys(created_keys)
        raise


@router.delete("/{project_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    project_id: int,
    image_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Delete the image and its associated registration record and files."""
    await _get_project(project_id, session)
    image = await _get_image(project_id, image_id, session)
    keys = [image.original_key, image.processed_key, *image.variant_keys.values()]
    record_id = image.record_id
    await session.delete(image)
    record = await session.get(RegistrationRecord, record_id)
    if record is not None and record.project_id == project_id:
        await session.delete(record)
    await session.commit()
    delete_storage_keys([key for key in keys if key])
    cleanup_empty_directories(project_id, record_id)