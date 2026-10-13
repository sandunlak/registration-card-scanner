"""Structured OCR request, job, and recognition-region schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class HandwritingRegion(BaseModel):
    """Normalized crop selection over the processed preview, used only by TrOCR."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def ensure_within_image(self) -> HandwritingRegion:
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("Handwriting region must remain within the processed image.")
        return self


class OcrStartRequest(BaseModel):
    handwriting_regions: list[HandwritingRegion] = Field(
        default_factory=list,
        max_length=20,
        description="Optional normalized text-line crops. TrOCR runs only for supplied regions.",
    )


class OcrJobRead(BaseModel):
    id: int
    project_id: int
    image_id: int
    status: Literal["queued", "processing", "completed", "failed"]
    error_code: str | None
    error_message: str | None
    attempt_count: int
    duration_ms: int | None
    result_count: int
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class OcrResultRead(BaseModel):
    id: int
    job_id: int
    image_id: int
    region_index: int
    text: str
    polygon: list[list[float]]
    coordinate_space: Literal["processed"]
    image_width: int
    image_height: int
    recognition_type: Literal["printed", "handwritten"]
    model_id: str
    model_version: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OcrResultsRead(BaseModel):
    job: OcrJobRead
    items: list[OcrResultRead]