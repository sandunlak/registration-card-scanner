"""Pydantic schemas for ProjectField."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import re
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class FieldType(str, Enum):
    TEXT = "text"
    PHONE = "phone"
    EMAIL = "email"
    DATE = "date"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class ValidationConfig(BaseModel):
    """Optional validation and UI presentation configuration for a field."""

    options: Optional[list[str]] = Field(
        default=None,
        description="Allowed options for single_select or multi_select field types.",
    )
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


class ProjectFieldBase(BaseModel):
    field_label: str = Field(min_length=1, max_length=255)
    field_type: FieldType
    required: bool = False
    display_order: int = 0
    validation_config: Optional[dict[str, Any]] = None


class ProjectFieldCreate(ProjectFieldBase):
    field_key: str = Field(min_length=1, max_length=100)

    @field_validator("field_key")
    @classmethod
    def validate_field_key(cls, v: str) -> str:
        # Standardize field_key to snake_case alphanumeric identifier
        cleaned = v.strip().lower().replace(" ", "_")
        if not re.match(r"^[a-z0-9_]+$", cleaned):
            raise ValueError(
                "field_key must contain only lowercase alphanumeric characters and underscores"
            )
        return cleaned


class ProjectFieldUpdate(BaseModel):
    field_label: Optional[str] = Field(default=None, min_length=1, max_length=255)
    field_type: Optional[FieldType] = None
    required: Optional[bool] = None
    display_order: Optional[int] = None
    validation_config: Optional[dict[str, Any]] = None


class ProjectFieldRead(ProjectFieldBase):
    id: int
    project_id: int
    field_key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FieldReorderRequest(BaseModel):
    """Request payload to set the order of fields in a project."""

    field_ids: list[int] = Field(
        min_length=1,
        description="List of field IDs in the desired display order.",
    )
