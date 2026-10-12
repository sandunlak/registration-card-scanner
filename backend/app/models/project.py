"""SQLModel database models for Project, ProjectField, and RegistrationRecord.

Models adhere strictly to the following domain rules:
- Identifiers, phone numbers, NICs, and passports are stored as strings to preserve leading zeros.
- Images are referenced by local path, never stored as raw blobs.
- Records and fields belong to a specific Project with foreign key relationships.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import JSON, Column, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel


def utc_now() -> datetime:
    """Return current UTC timestamp without timezone offset issues."""
    return datetime.now(timezone.utc)


class ProjectField(SQLModel, table=True):
    """Configurable field definition associated with a specific Project.

    Supported field types:
    - text
    - phone (enforced as string to preserve leading zeros)
    - email
    - date (YYYY-MM-DD)
    - number
    - boolean
    - single_select
    - multi_select
    """

    __tablename__ = "projectfield"
    __table_args__ = (
        UniqueConstraint("project_id", "field_key", name="uq_project_field_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)
    field_key: str = Field(index=True, max_length=100, nullable=False)
    field_label: str = Field(max_length=255, nullable=False)
    field_type: str = Field(max_length=50, nullable=False)
    required: bool = Field(default=False)
    display_order: int = Field(default=0, index=True)
    validation_config: Optional[dict[str, Any]] = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": func.now()},
    )

    # Relationship back to project
    project: Optional["Project"] = Relationship(back_populates="fields")


class RegistrationRecord(SQLModel, table=True):
    """Extracted or manually-entered registration record for a card in a Project.

    - extracted_data: JSON dictionary where keys correspond to ProjectField.field_key.
      Identifiers/phones are stored as strings.
    - review_status: "pending" | "reviewed" | "needs_review"
    - source_image_path: relative or absolute path on disk (never image blobs).
    """

    __tablename__ = "registrationrecord"

    id: Optional[int] = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True, nullable=False)
    source_image_path: Optional[str] = Field(default=None, max_length=1024)
    extracted_data: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    review_status: str = Field(
        default="pending",
        index=True,
        max_length=50,
    )  # "pending" | "reviewed" | "needs_review"
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": func.now()},
    )

    # Relationship back to project
    project: Optional["Project"] = Relationship(back_populates="records")


class Project(SQLModel, table=True):
    """Event or intake project grouping registration cards and custom field configurations."""

    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255, nullable=False)
    description: Optional[str] = Field(default=None)
    event_name: Optional[str] = Field(default=None, max_length=255)
    status: str = Field(default="active", index=True, max_length=50)  # "active" | "archived"
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"onupdate": func.now()},
    )

    # Relationships with explicit model references
    fields: list[ProjectField] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ProjectField.display_order",
            "lazy": "selectin",
        },
    )
    records: list[RegistrationRecord] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )
