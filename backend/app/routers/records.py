"""API router for RegistrationRecord management within a Project."""

from __future__ import annotations

import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.models.project import Project, ProjectField, RegistrationRecord
from app.schemas.record import (
    RecordReviewStatus,
    RegistrationRecordCreate,
    RegistrationRecordUpdate,
    RegistrationRecordRead,
    RecordListResponse,
)
from app.services.record_validator import sanitize_and_validate_record_data

router = APIRouter(prefix="", tags=["records"])


async def _get_project_or_404(project_id: int, session: AsyncSession) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")
    return project


@router.get("/{project_id}/records", response_model=RecordListResponse)
async def list_records(
    project_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    review_status: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> RecordListResponse:
    """List records for a project with pagination and optional review_status filter."""
    await _get_project_or_404(project_id, session)

    count_stmt = select(func.count(RegistrationRecord.id)).where(
        RegistrationRecord.project_id == project_id
    )
    if review_status:
        count_stmt = count_stmt.where(RegistrationRecord.review_status == review_status)

    total = (await session.exec(count_stmt)).one()

    offset = (page - 1) * limit
    stmt = (
        select(RegistrationRecord)
        .where(RegistrationRecord.project_id == project_id)
        .order_by(RegistrationRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if review_status:
        stmt = stmt.where(RegistrationRecord.review_status == review_status)

    records = (await session.exec(stmt)).all()
    pages = math.ceil(total / limit) if total > 0 else 1

    return RecordListResponse(
        items=[RegistrationRecordRead.model_validate(r) for r in records],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.post(
    "/{project_id}/records",
    response_model=RegistrationRecordRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_record(
    project_id: int,
    data: RegistrationRecordCreate,
    session: AsyncSession = Depends(get_session),
) -> RegistrationRecordRead:
    """Create a new registration record.

    Validates extracted_data against project's configured fields:
    - Enforces required fields.
    - Preserves string formatting for phone numbers and identifiers.
    - Validates data types.
    """
    project = await _get_project_or_404(project_id, session)

    fields_stmt = (
        select(ProjectField)
        .where(ProjectField.project_id == project_id)
        .order_by(ProjectField.display_order.asc())
    )
    project_fields = (await session.exec(fields_stmt)).all()

    # Validate and sanitize data
    sanitized_data = sanitize_and_validate_record_data(
        extracted_data=data.extracted_data,
        project_fields=list(project_fields),
        check_required=True,
    )

    review_status_val = (
        data.review_status.value
        if isinstance(data.review_status, RecordReviewStatus)
        else (data.review_status or "pending")
    )

    record = RegistrationRecord(
        project_id=project.id,  # type: ignore[arg-type]
        source_image_path=data.source_image_path,
        extracted_data=sanitized_data,
        review_status=review_status_val,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    return RegistrationRecordRead.model_validate(record)


@router.get("/{project_id}/records/{record_id}", response_model=RegistrationRecordRead)
async def get_record(
    project_id: int,
    record_id: int,
    session: AsyncSession = Depends(get_session),
) -> RegistrationRecordRead:
    """Get a record by ID. Strictly verifies that record belongs to project_id."""
    await _get_project_or_404(project_id, session)

    record = await session.get(RegistrationRecord, record_id)
    if not record or record.project_id != project_id:
        raise NotFoundError(
            f"Record {record_id} not found in project {project_id}."
        )

    return RegistrationRecordRead.model_validate(record)


@router.patch("/{project_id}/records/{record_id}", response_model=RegistrationRecordRead)
async def update_record(
    project_id: int,
    record_id: int,
    data: RegistrationRecordUpdate,
    session: AsyncSession = Depends(get_session),
) -> RegistrationRecordRead:
    """Update record data or review status. Strictly verifies that record belongs to project_id."""
    await _get_project_or_404(project_id, session)

    record = await session.get(RegistrationRecord, record_id)
    if not record or record.project_id != project_id:
        raise NotFoundError(
            f"Record {record_id} not found in project {project_id}."
        )

    if data.extracted_data is not None:
        fields_stmt = (
            select(ProjectField)
            .where(ProjectField.project_id == project_id)
            .order_by(ProjectField.display_order.asc())
        )
        project_fields = (await session.exec(fields_stmt)).all()

        # Merge with existing data
        merged = {**record.extracted_data, **data.extracted_data}
        sanitized = sanitize_and_validate_record_data(
            extracted_data=merged,
            project_fields=list(project_fields),
            check_required=False,
        )
        record.extracted_data = sanitized

    if data.review_status is not None:
        record.review_status = (
            data.review_status.value
            if isinstance(data.review_status, RecordReviewStatus)
            else data.review_status
        )

    if data.source_image_path is not None:
        record.source_image_path = data.source_image_path

    session.add(record)
    await session.commit()
    await session.refresh(record)

    return RegistrationRecordRead.model_validate(record)
