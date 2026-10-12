"""Pydantic schemas for Project."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.field import ProjectFieldCreate, ProjectFieldRead


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    event_name: Optional[str] = Field(default=None, max_length=255)


class ProjectCreate(ProjectBase):
    fields: Optional[list[ProjectFieldCreate]] = Field(
        default=None,
        description="Optional initial fields to configure during project creation.",
    )


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    event_name: Optional[str] = Field(default=None, max_length=255)
    status: Optional[ProjectStatus] = None


class ProjectRead(ProjectBase):
    id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    field_count: int = 0
    record_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailRead(ProjectBase):
    id: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    fields: list[ProjectFieldRead] = []
    record_count: int = 0

    model_config = ConfigDict(from_attributes=True)
