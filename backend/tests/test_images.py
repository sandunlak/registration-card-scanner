"""API tests for private image upload, processing, and lifecycle operations."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient
from PIL import Image, ImageDraw
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.models.image import ImageAsset
from app.models.project import Project, ProjectField, RegistrationRecord
from app.services.image_storage import resolve_storage_key


@pytest.fixture
def image_settings(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(settings, "images_dir", str(tmp_path / "private-images"))
    monkeypatch.setattr(settings, "max_upload_size_mb", 20)
    monkeypatch.setattr(settings, "max_image_pixels", 40_000_000)
    monkeypatch.setattr(settings, "max_images_per_batch", 10)
    return tmp_path / "private-images"


def make_card(format_name: str = "PNG", size: tuple[int, int] = (1000, 700)) -> bytes:
    image = Image.new("RGB", size, (55, 55, 55))
    draw = ImageDraw.Draw(image)
    draw.rectangle((100, 70, size[0] - 100, size[1] - 70), fill=(235, 230, 215))
    buffer = io.BytesIO()
    image.save(buffer, format=format_name)
    return buffer.getvalue()


async def create_project(client: AsyncClient, name: str = "Image Project") -> int:
    response = await client.post("/api/projects", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_upload_and_preview_creates_one_record_and_private_files(
    client: AsyncClient, image_settings
) -> None:
    project_id = await create_project(client)
    response = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.png", make_card(), "image/png")},
    )

    assert response.status_code == 201
    image = response.json()
    assert image["status"] == "ready"
    assert image["record_id"] == 1
    assert "boundary_not_detected" not in image["metadata"]["quality_warnings"]
    assert "original_key" not in image
    assert len(list(image_settings.rglob("*.*"))) == 6

    preview = await client.get(
        f"/api/projects/{project_id}/images/{image['id']}/preview?variant=processed"
    )
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "private, no-store"
    assert preview.content.startswith(b"\xff\xd8")
    records = await client.get(f"/api/projects/{project_id}/records")
    assert records.json()["total"] == 1


@pytest.mark.asyncio
async def test_batch_upload_returns_individual_statuses(client: AsyncClient, image_settings) -> None:
    project_id = await create_project(client)
    response = await client.post(
        f"/api/projects/{project_id}/images/batch",
        files=[
            ("files", ("first.png", make_card(), "image/png")),
            ("files", ("bad.gif", b"no", "image/gif")),
            ("files", ("second.webp", make_card("WEBP"), "image/webp")),
        ],
    )

    assert response.status_code == 201
    outcomes = response.json()["items"]
    assert outcomes[0]["image"]["status"] == "ready"
    assert "failure" in outcomes[1]
    assert outcomes[2]["image"]["status"] == "ready"
    assert len((await client.get(f"/api/projects/{project_id}/records")).json()["items"]) == 2


@pytest.mark.asyncio
async def test_invalid_content_and_dimensions_are_rejected(client: AsyncClient, image_settings, monkeypatch) -> None:
    project_id = await create_project(client)
    mismatch = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.jpg", make_card(), "image/jpeg")},
    )
    corrupted = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.png", b"not image bytes", "image/png")},
    )
    assert mismatch.status_code == 415
    assert corrupted.status_code == 422

    monkeypatch.setattr(settings, "max_upload_size_mb", 1)
    oversized = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.png", b"x" * (1024 * 1024 + 1), "image/png")},
    )
    assert oversized.status_code == 413
    monkeypatch.setattr(settings, "max_image_pixels", 100)
    excessive_pixels = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.png", make_card(), "image/png")},
    )
    assert excessive_pixels.status_code == 413


@pytest.mark.asyncio
async def test_project_isolation_retry_replace_and_safe_delete(
    client: AsyncClient, image_settings
) -> None:
    project_id = await create_project(client, "Project A")
    other_project_id = await create_project(client, "Project B")
    upload = await client.post(
        f"/api/projects/{project_id}/images",
        files={"file": ("card.png", make_card(), "image/png")},
    )
    image = upload.json()
    image_id = image["id"]
    assert (await client.get(f"/api/projects/{other_project_id}/images/{image_id}")).status_code == 404
    assert (
        await client.get(
            f"/api/projects/{other_project_id}/images/{image_id}/preview?variant=original"
        )
    ).status_code == 404

    retry = await client.post(f"/api/projects/{project_id}/images/{image_id}/retry")
    assert retry.status_code == 200
    assert retry.json()["record_id"] == image["record_id"]
    adjusted = await client.post(
        f"/api/projects/{project_id}/images/{image_id}/adjust",
        json={"rotation": 90, "crop": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8}},
    )
    assert adjusted.status_code == 200
    assert adjusted.json()["rotation"] == 90
    assert adjusted.json()["crop"]["width"] == 0.8
    replacement = await client.post(
        f"/api/projects/{project_id}/images/{image_id}/replace",
        files={"file": ("replacement.webp", make_card("WEBP"), "image/webp")},
    )
    assert replacement.status_code == 200
    assert replacement.json()["record_id"] == image["record_id"]
    assert (await client.get(f"/api/projects/{project_id}/records")).json()["total"] == 1

    deleted = await client.delete(f"/api/projects/{project_id}/images/{image_id}")
    assert deleted.status_code == 204
    assert not list(image_settings.rglob("*.*"))
    assert (await client.get(f"/api/projects/{project_id}/records")).json()["total"] == 0


@pytest.mark.asyncio
async def test_database_failure_removes_created_files(
    client: AsyncClient, test_session, image_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_id = await create_project(client)

    async def fail_commit() -> None:
        raise RuntimeError("simulated database failure")

    monkeypatch.setattr(test_session, "commit", fail_commit)
    with pytest.raises(RuntimeError, match="simulated database failure"):
        await client.post(
            f"/api/projects/{project_id}/images",
            files={"file": ("card.png", make_card(), "image/png")},
        )
    monkeypatch.undo()

    assert not list(image_settings.rglob("*.*"))
    assert (await test_session.exec(select(ImageAsset))).all() == []
    assert (await test_session.exec(select(RegistrationRecord))).all() == []


@pytest.mark.asyncio
async def test_adding_image_schema_preserves_existing_project_and_record_data(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy.sqlite'}")
    legacy_tables = [Project.__table__, ProjectField.__table__, RegistrationRecord.__table__]
    async with engine.begin() as connection:
        await connection.run_sync(lambda sync: SQLModel.metadata.create_all(sync, tables=legacy_tables))

    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessions() as session:
        project = Project(name="Existing project")
        session.add(project)
        await session.commit()
        record = RegistrationRecord(
            project_id=int(project.id),
            extracted_data={"reference": "00042"},
            review_status="reviewed",
        )
        session.add(record)
        await session.commit()
        record_id = int(record.id)

    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    async with sessions() as session:
        preserved = await session.get(RegistrationRecord, record_id)
        assert preserved is not None
        assert preserved.extracted_data == {"reference": "00042"}
        assert preserved.review_status == "reviewed"
        assert (await session.exec(select(ImageAsset))).all() == []
    await engine.dispose()


def test_storage_keys_cannot_escape_configured_root(image_settings) -> None:
    with pytest.raises(Exception, match="Invalid image storage reference"):
        resolve_storage_key("../outside.jpg")