"""Pydantic schemas for RegistrationRecord."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class RecordReviewStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"
    NEEDS_REVIEW = "needs_review"


class RegistrationRecordBase(BaseModel):
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary mapping field_key to extracted/entered value. Phones/IDs are stored as strings.",
    )
    review_status: RecordReviewStatus = RecordReviewStatus.PENDING
    source_image_path: Optional[str] = None


class RegistrationRecordCreate(BaseModel):
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary mapping field_key to extracted/entered value.",
    )
    review_status: Optional[RecordReviewStatus] = RecordReviewStatus.PENDING
    source_image_path: Optional[str] = None


class RegistrationRecordUpdate(BaseModel):
    extracted_data: Optional[dict[str, Any]] = None
    review_status: Optional[RecordReviewStatus] = None
    source_image_path: Optional[str] = None


class RegistrationRecordRead(RegistrationRecordBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordListResponse(BaseModel):
    """Paginated list of registration records."""

    items: list[RegistrationRecordRead]
    total: int
    page: int
    limit: int
    pages: int
