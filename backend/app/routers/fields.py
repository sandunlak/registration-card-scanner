"""API router for ProjectField management within a Project."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError, ValidationError
from app.models.project import Project, ProjectField
from app.schemas.field import (
    ProjectFieldCreate,
    ProjectFieldUpdate,
    ProjectFieldRead,
    FieldReorderRequest,
)

router = APIRouter(prefix="", tags=["fields"])


async def _get_project_or_404(project_id: int, session: AsyncSession) -> Project:
    """Fetch project or raise NotFoundError."""
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")
    return project


@router.get("/{project_id}/fields", response_model=list[ProjectFieldRead])
async def list_fields(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[ProjectFieldRead]:
    """List all configured fields for a project, ordered by display_order."""
    await _get_project_or_404(project_id, session)

    stmt = (
        select(ProjectField)
        .where(ProjectField.project_id == project_id)
        .order_by(ProjectField.display_order.asc(), ProjectField.id.asc())
    )
    result = await session.exec(stmt)
    fields = result.all()
    return [ProjectFieldRead.model_validate(f) for f in fields]


@router.post(
    "/{project_id}/fields",
    response_model=ProjectFieldRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_field(
    project_id: int,
    data: ProjectFieldCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectFieldRead:
    """Create a new field definition for a project."""
    await _get_project_or_404(project_id, session)

    # Check for duplicate field_key within this project
    existing_stmt = select(ProjectField).where(
        ProjectField.project_id == project_id,
        ProjectField.field_key == data.field_key,
    )
    existing = (await session.exec(existing_stmt)).first()
    if existing:
        raise ValidationError(
            f"Field with key '{data.field_key}' already exists in project {project_id}."
        )

    # Calculate next display_order if not explicitly set
    display_order = data.display_order
    if display_order <= 0:
        max_order_stmt = select(func.coalesce(func.max(ProjectField.display_order), 0)).where(
            ProjectField.project_id == project_id
        )
        max_order = (await session.exec(max_order_stmt)).one()
        display_order = max_order + 1

    field = ProjectField(
        project_id=project_id,
        field_key=data.field_key,
        field_label=data.field_label,
        field_type=data.field_type.value,
        required=data.required,
        display_order=display_order,
        validation_config=data.validation_config,
    )
    session.add(field)
    await session.commit()
    await session.refresh(field)

    return ProjectFieldRead.model_validate(field)


@router.get("/{project_id}/fields/{field_id}", response_model=ProjectFieldRead)
async def get_field(
    project_id: int,
    field_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProjectFieldRead:
    """Get a single field. Strictly enforces that the field belongs to project_id."""
    await _get_project_or_404(project_id, session)

    field = await session.get(ProjectField, field_id)
    if not field or field.project_id != project_id:
        raise NotFoundError(
            f"Field {field_id} not found in project {project_id}."
        )

    return ProjectFieldRead.model_validate(field)


@router.patch("/{project_id}/fields/{field_id}", response_model=ProjectFieldRead)
async def update_field(
    project_id: int,
    field_id: int,
    data: ProjectFieldUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProjectFieldRead:
    """Update a field. Strictly enforces that the field belongs to project_id."""
    await _get_project_or_404(project_id, session)

    field = await session.get(ProjectField, field_id)
    if not field or field.project_id != project_id:
        raise NotFoundError(
            f"Field {field_id} not found in project {project_id}."
        )

    if data.field_label is not None:
        field.field_label = data.field_label
    if data.field_type is not None:
        field.field_type = data.field_type.value
    if data.required is not None:
        field.required = data.required
    if data.display_order is not None:
        field.display_order = data.display_order
    if data.validation_config is not None:
        field.validation_config = data.validation_config

    session.add(field)
    await session.commit()
    await session.refresh(field)

    return ProjectFieldRead.model_validate(field)


@router.delete("/{project_id}/fields/{field_id}")
async def delete_field(
    project_id: int,
    field_id: int,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delete a field. Strictly enforces that the field belongs to project_id."""
    await _get_project_or_404(project_id, session)

    field = await session.get(ProjectField, field_id)
    if not field or field.project_id != project_id:
        raise NotFoundError(
            f"Field {field_id} not found in project {project_id}."
        )

    await session.delete(field)
    await session.commit()

    return {"status": "deleted", "id": field_id}


@router.post("/{project_id}/fields/reorder", response_model=list[ProjectFieldRead])
async def reorder_fields(
    project_id: int,
    data: FieldReorderRequest,
    session: AsyncSession = Depends(get_session),
) -> list[ProjectFieldRead]:
    """Reorder fields according to the provided list of field_ids."""
    await _get_project_or_404(project_id, session)

    stmt = select(ProjectField).where(ProjectField.project_id == project_id)
    fields = (await session.exec(stmt)).all()
    field_map = {f.id: f for f in fields}

    # Verify that all field_ids in data belong to this project
    for fid in data.field_ids:
        if fid not in field_map:
            raise ValidationError(
                f"Field ID {fid} does not belong to project {project_id}."
            )

    # Update display order
    for idx, fid in enumerate(data.field_ids):
        f = field_map[fid]
        f.display_order = idx + 1
        session.add(f)

    await session.commit()

    # Re-fetch in new order
    ordered_stmt = (
        select(ProjectField)
        .where(ProjectField.project_id == project_id)
        .order_by(ProjectField.display_order.asc(), ProjectField.id.asc())
    )
    updated_fields = (await session.exec(ordered_stmt)).all()
    return [ProjectFieldRead.model_validate(f) for f in updated_fields]
