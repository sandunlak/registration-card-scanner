"""Database metadata for private, locally stored card images."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, func
from sqlmodel import Field, SQLModel

from app.models.project import utc_now


class ImageAsset(SQLModel, table=True):
    __tablename__ = "imageasset"

    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)
    record_id: int = Field(foreign_key="registrationrecord.id", unique=True, nullable=False)
    original_key: str = Field(max_length=1024, nullable=False)
    processed_key: str | None = Field(default=None, max_length=1024)
    variant_keys: dict[str, str] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: str = Field(default="uploaded", index=True, max_length=50)
    metadata_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    error_message: str | None = Field(default=None, max_length=500)
    rotation: int = Field(default=0)
    crop: dict[str, float] | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    created_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"server_default": func.now()})
    updated_at: datetime = Field(default_factory=utc_now, sa_column_kwargs={"onupdate": func.now()})