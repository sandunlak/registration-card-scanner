"""Request and response schemas for card image workflows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ImageAssetRead(BaseModel):
    id: int
    project_id: int
    record_id: int
    status: Literal["uploaded", "processing", "ready", "failed"]
    metadata: dict[str, Any]
    variants: list[str]
    rotation: Literal[0, 90, 180, 270]
    crop: dict[str, float] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ImageBatchRead(BaseModel):
    items: list[ImageAssetRead]


class ImageUploadFailure(BaseModel):
    status: Literal["failed"] = "failed"
    error_message: str


class ImageUploadOutcome(BaseModel):
    image: ImageAssetRead | None = None
    failure: ImageUploadFailure | None = None


class ImageBatchUploadRead(BaseModel):
    items: list[ImageUploadOutcome]


class ImageAdjust(BaseModel):
    rotation: Literal[0, 90, 180, 270] = 0
    crop: dict[str, float] | None = Field(
        default=None,
        description="Normalized x, y, width, height fractions for a manual crop.",
    )


class ImageUploadResult(BaseModel):
    image: ImageAssetRead