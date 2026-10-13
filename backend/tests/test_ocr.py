"""OCR jobs use mocked recognizers so routine tests need no model weights."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.exceptions import OCRUnavailableError
from app.models.image import ImageAsset
from app.models.ocr import OcrJob, OcrResult
from app.models.project import Project, ProjectField, RegistrationRecord
from app.schemas.ocr import HandwritingRegion, OcrResultRead
from app.services.image_storage import resolve_storage_key
from app.services.ocr_service import RecognizedRegion


def use_test_session_factory(monkeypatch: pytest.MonkeyPatch, test_session: AsyncSession) -> None:
    from app.routers import ocr as ocr_router

    factory = async_sessionmaker(
        bind=test_session.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    monkeypatch.setattr(ocr_router, "AsyncSessionLocal", factory)


@pytest.fixture
def ocr_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(settings, "images_dir", str(tmp_path / "images"))
    monkeypatch.setattr(settings, "ocr_models_dir", str(tmp_path / "models"))
    monkeypatch.setattr(settings, "ocr_max_handwriting_regions", 20)
    return tmp_path


def sample_png() -> bytes:
    image = Image.new("RGB", (800, 600), "white")
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def create_uploaded_image(client: AsyncClient) -> tuple[int, int]:
    project = await client.post("/api/projects", json={"name": "OCR Test Project"})
    assert project.status_code == 201
    project_id = project.json()["id"]
    upload = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("synthetic.png", sample_png(), "image/png")},
    )
    assert upload.status_code == 201
    image = upload.json()
    return project_id, image["id"]


class FakeOcrPipeline:
    def __init__(self, regions: list[RecognizedRegion] | None = None, fail: bool = False):
        self.regions = regions or []
        self.fail = fail
        self.calls = 0

    def recognize(
        self, image_path, handwriting_regions: list[HandwritingRegion]
    ) -> tuple[list[RecognizedRegion], int, int]:
        self.calls += 1
        if self.fail:
            raise OCRUnavailableError("Local OCR models are not installed.")
        return self.regions, 800, 600


def sample_regions() -> list[RecognizedRegion]:
    return [
        RecognizedRegion(
            text="Synthetic printed label",
            polygon=[[20.0, 20.0], [300.0, 20.0], [300.0, 60.0], [20.0, 60.0]],
            recognition_type="printed",
            model_id="PaddleOCR/test-det+test-rec",
            model_version="mock-1",
            confidence=0.94,
            extra_metadata={"detection_confidence": 0.98},
        ),
        RecognizedRegion(
            text="Synthetic handwritten line",
            polygon=[[100.0, 150.0], [500.0, 150.0], [500.0, 220.0], [100.0, 220.0]],
            recognition_type="handwritten",
            model_id="microsoft/trocr-base-handwritten",
            model_version="mock-revision",
            confidence=None,
            extra_metadata={"confidence_available": False},
        ),
    ]


@pytest.mark.asyncio
async def test_job_results_are_scoped_deduplicated_and_preserve_record_data(
    client: AsyncClient, test_session: AsyncSession, ocr_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers import ocr as ocr_router

    project_id, image_id = await create_uploaded_image(client)
    use_test_session_factory(monkeypatch, test_session)
    image = await test_session.get(ImageAsset, image_id)
    assert image is not None
    record = await test_session.get(RegistrationRecord, image.record_id)
    assert record is not None
    record.extracted_data = {"field_alpha": "synthetic-manual-override", "field_beta": "synthetic-id"}
    record.review_status = "reviewed"
    test_session.add(record)
    await test_session.commit()

    other_project = await client.post("/api/projects", json={"name": "Other Project"})
    other_project_id = other_project.json()["id"]
    pipeline = FakeOcrPipeline(sample_regions())
    monkeypatch.setattr(ocr_router, "create_ocr_pipeline", lambda: pipeline)
    request_body = {"handwriting_regions": [{"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.15}]}

    started = await client.post(
        f"/api/projects/{project_id}/images/{image_id}/ocr", json=request_body
    )
    assert started.status_code == 202
    job_id = started.json()["id"]
    status_response = await client.get(
        f"/api/projects/{project_id}/images/{image_id}/ocr/{job_id}"
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed", (
        status_response.json()["error_code"],
        status_response.json()["error_message"],
    )
    assert status_response.json()["result_count"] == 2

    results = await client.get(
        f"/api/projects/{project_id}/images/{image_id}/ocr/{job_id}/results"
    )
    assert results.status_code == 200
    assert [item["recognition_type"] for item in results.json()["items"]] == [
        "printed",
        "handwritten",
    ]
    assert results.json()["items"][0]["confidence"] == 0.94
    assert results.json()["items"][1]["confidence"] is None
    assert results.json()["items"][0]["coordinate_space"] == "processed"

    duplicate = await client.post(
        f"/api/projects/{project_id}/images/{image_id}/ocr", json=request_body
    )
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == job_id
    assert (await test_session.exec(select(OcrJob))).all().__len__() == 1
    assert pipeline.calls == 1

    cross_project = await client.get(
        f"/api/projects/{other_project_id}/images/{image_id}/ocr/{job_id}"
    )
    assert cross_project.status_code == 404
    preserved = await test_session.get(RegistrationRecord, image.record_id)
    assert preserved is not None
    assert preserved.extracted_data == {
        "field_alpha": "synthetic-manual-override",
        "field_beta": "synthetic-id",
    }
    assert preserved.review_status == "reviewed"


@pytest.mark.asyncio
async def test_empty_results_complete_and_failed_job_retries_in_place(
    client: AsyncClient, test_session: AsyncSession, ocr_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.routers import ocr as ocr_router

    use_test_session_factory(monkeypatch, test_session)
    project_id, image_id = await create_uploaded_image(client)
    not_started = await client.get(f"/api/projects/{project_id}/images/{image_id}/ocr")
    assert not_started.status_code == 200
    assert not_started.json() is None
    empty_pipeline = FakeOcrPipeline()
    monkeypatch.setattr(ocr_router, "create_ocr_pipeline", lambda: empty_pipeline)
    empty_job = await client.post(f"/api/projects/{project_id}/images/{image_id}/ocr")
    assert empty_job.status_code == 202
    completed = await client.get(
        f"/api/projects/{project_id}/images/{image_id}/ocr/{empty_job.json()['id']}"
    )
    assert completed.json()["status"] == "completed", (
        completed.json()["error_code"],
        completed.json()["error_message"],
    )
    empty_results = await client.get(
        f"/api/projects/{project_id}/images/{image_id}/ocr/{empty_job.json()['id']}/results"
    )
    assert empty_results.json()["items"] == []

    project_id2, image_id2 = await create_uploaded_image(client)
    failed_pipeline = FakeOcrPipeline(fail=True)
    monkeypatch.setattr(ocr_router, "create_ocr_pipeline", lambda: failed_pipeline)
    failed = await client.post(f"/api/projects/{project_id2}/images/{image_id2}/ocr")
    job_id = failed.json()["id"]
    failed_status = await client.get(
        f"/api/projects/{project_id2}/images/{image_id2}/ocr/{job_id}"
    )
    assert failed_status.json()["status"] == "failed"
    assert failed_status.json()["error_code"] == "models_unavailable"

    ready_pipeline = FakeOcrPipeline(sample_regions()[:1])
    monkeypatch.setattr(ocr_router, "create_ocr_pipeline", lambda: ready_pipeline)
    retry = await client.post(
        f"/api/projects/{project_id2}/images/{image_id2}/ocr/{job_id}/retry"
    )
    assert retry.status_code == 202
    assert retry.json()["id"] == job_id
    assert retry.json()["attempt_count"] == 2
    assert (await test_session.exec(select(OcrJob).where(OcrJob.image_id == image_id2))).all().__len__() == 1


@pytest.mark.asyncio
async def test_missing_processed_image_is_a_safe_failed_job(
    client: AsyncClient,
    test_session: AsyncSession,
    ocr_settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_test_session_factory(monkeypatch, test_session)
    project_id, image_id = await create_uploaded_image(client)
    image = await test_session.get(ImageAsset, image_id)
    assert image is not None and image.processed_key is not None
    resolve_storage_key(image.processed_key).unlink()

    started = await client.post(f"/api/projects/{project_id}/images/{image_id}/ocr")
    job_id = started.json()["id"]
    job = await client.get(f"/api/projects/{project_id}/images/{image_id}/ocr/{job_id}")
    assert job.json()["status"] == "failed"
    assert job.json()["error_code"] == "unreadable_image"
    assert "filesystem" not in job.json()["error_message"].lower()


@pytest.mark.asyncio
async def test_alembic_upgrade_preserves_existing_database_data(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    backend_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'existing.sqlite'}"
    engine = create_async_engine(database_url)
    legacy_tables = [
        Project.__table__,
        ProjectField.__table__,
        RegistrationRecord.__table__,
        ImageAsset.__table__,
    ]
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: SQLModel.metadata.create_all(sync, tables=legacy_tables))
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as session:
        project = Project(name="Existing project")
        session.add(project)
        await session.commit()
        record = RegistrationRecord(
            project_id=int(project.id),
            extracted_data={"field_beta": "synthetic-id"},
            review_status="reviewed",
        )
        session.add(record)
        await session.commit()
        record_id = int(record.id)
    await engine.dispose()

    monkeypatch.setattr(settings, "database_url", database_url)
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    command.upgrade(config, "head")

    engine = create_async_engine(database_url)
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as session:
        record = await session.get(RegistrationRecord, record_id)
        assert record is not None
        assert record.extracted_data == {"field_beta": "synthetic-id"}
        assert record.review_status == "reviewed"
        assert (await session.exec(select(OcrJob))).all() == []
        assert (await session.exec(select(OcrResult))).all() == []
    await engine.dispose()


def test_handwriting_crops_are_normalized_and_edit_metrics_are_correct() -> None:
    from app.services.ocr_evaluation import edit_distance, transcription_errors

    crop = HandwritingRegion(x=0.1, y=0.2, width=0.3, height=0.1)
    assert crop.x + crop.width <= 1
    with pytest.raises(ValueError):
        HandwritingRegion(x=0.8, y=0.2, width=0.3, height=0.1)
    assert edit_distance("cat", "cut") == 1
    assert transcription_errors("Name 1", "name I") == (1, 6, 1, 2)
    assert transcription_errors("alpha beta", "alpha lengthy beta")[2:] == (1, 2)


def test_missing_local_models_fail_without_importing_ocr_runtime(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.ocr_service import create_ocr_pipeline

    monkeypatch.setattr(settings, "ocr_models_dir", str(tmp_path / "empty-model-cache"))
    with pytest.raises(OCRUnavailableError, match="Run `python -m app.services.ocr_setup`"):
        create_ocr_pipeline()


def test_ocr_confidence_is_optional_but_bounded() -> None:
    from pydantic import ValidationError

    base = {
        "id": 1,
        "job_id": 1,
        "image_id": 1,
        "region_index": 0,
        "text": "mock text",
        "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "coordinate_space": "processed",
        "image_width": 100,
        "image_height": 100,
        "recognition_type": "handwritten",
        "model_id": "mock",
        "model_version": "1",
        "extra_metadata": {},
        "created_at": "2026-10-13T00:00:00Z",
    }
    assert OcrResultRead.model_validate({**base, "confidence": None}).confidence is None
    with pytest.raises(ValidationError):
        OcrResultRead.model_validate({**base, "confidence": 1.2})