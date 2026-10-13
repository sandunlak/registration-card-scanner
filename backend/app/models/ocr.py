"""Durable OCR job and region results, kept separate from registration data."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, UniqueConstraint, func
from sqlmodel import Field, SQLModel

from app.models.project import utc_now


class OcrJob(SQLModel, table=True):
    __tablename__ = "ocrjob"
    __table_args__ = (UniqueConstraint("image_id", name="uq_ocrjob_image_id"),)

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)
    image_id: int = Field(foreign_key="imageasset.id", index=True, nullable=False)
    status: str = Field(default="queued", index=True, max_length=32)
    handwriting_regions: list[dict[str, float]] = Field(
        default_factory=list, sa_column=Column(JSON, nullable=False)
    )
    error_code: str | None = Field(default=None, max_length=64)
    error_message: str | None = Field(default=None, max_length=500)
    attempt_count: int = Field(default=1)
    duration_ms: int | None = Field(default=None)
    requested_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": func.now()})


class OcrResult(SQLModel, table=True):
    __tablename__ = "ocrresult"
    __table_args__ = (
        UniqueConstraint("job_id", "region_index", name="uq_ocrresult_job_region"),
    )

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)
    image_id: int = Field(foreign_key="imageasset.id", index=True, nullable=False)
    job_id: int = Field(foreign_key="ocrjob.id", index=True, nullable=False)
    region_index: int = Field(nullable=False)
    text: str = Field(default="", max_length=20_000)
    polygon: list[list[float]] = Field(sa_column=Column(JSON, nullable=False))
    coordinate_space: str = Field(default="processed", max_length=32)
    image_width: int = Field(nullable=False)
    image_height: int = Field(nullable=False)
    recognition_type: str = Field(default="printed", max_length=32)
    model_id: str = Field(max_length=255, nullable=False)
    model_version: str = Field(max_length=100, nullable=False)
    confidence: float | None = Field(default=None)
    extra_metadata: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})