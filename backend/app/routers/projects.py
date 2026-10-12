"""API router for Project management."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.database import get_session
from app.core.exceptions import NotFoundError
from app.models.project import Project, ProjectField, RegistrationRecord
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectRead,
    ProjectDetailRead,
)

router = APIRouter(prefix="", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> list[ProjectRead]:
    """List all projects with counts of fields and records."""
    query = select(Project).order_by(Project.created_at.desc())
    if status_filter:
        query = query.where(Project.status == status_filter)

    result = await session.exec(query)
    projects = result.all()

    response: list[ProjectRead] = []
    for p in projects:
        # Count fields and records
        f_count_stmt = select(func.count(ProjectField.id)).where(ProjectField.project_id == p.id)
        r_count_stmt = select(func.count(RegistrationRecord.id)).where(RegistrationRecord.project_id == p.id)

        f_res = await session.exec(f_count_stmt)
        r_res = await session.exec(r_count_stmt)

        field_count = f_res.one()
        record_count = r_res.one()

        response.append(
            ProjectRead(
                id=p.id,  # type: ignore[arg-type]
                name=p.name,
                description=p.description,
                event_name=p.event_name,
                status=p.status,  # type: ignore[arg-type]
                created_at=p.created_at,
                updated_at=p.updated_at,
                field_count=field_count,
                record_count=record_count,
            )
        )
    return response


@router.post("", response_model=ProjectDetailRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailRead:
    """Create a new project, optionally with initial configured fields."""
    project = Project(
        name=data.name,
        description=data.description,
        event_name=data.event_name,
        status="active",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    # Optional initial fields
    if data.fields:
        for idx, f_data in enumerate(data.fields):
            field = ProjectField(
                project_id=project.id,  # type: ignore[arg-type]
                field_key=f_data.field_key,
                field_label=f_data.field_label,
                field_type=f_data.field_type.value,
                required=f_data.required,
                display_order=f_data.display_order or (idx + 1),
                validation_config=f_data.validation_config,
            )
            session.add(field)
        await session.commit()
        await session.refresh(project)

    return ProjectDetailRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectDetailRead)
async def get_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProjectDetailRead:
    """Get project details including all configured fields and record count."""
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")

    r_count_stmt = select(func.count(RegistrationRecord.id)).where(RegistrationRecord.project_id == project.id)
    r_res = await session.exec(r_count_stmt)
    record_count = r_res.one()

    detail = ProjectDetailRead.model_validate(project)
    detail.record_count = record_count
    return detail


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: int,
    data: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Update project metadata."""
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.event_name is not None:
        project.event_name = data.event_name
    if data.status is not None:
        project.status = data.status.value

    session.add(project)
    await session.commit()
    await session.refresh(project)

    f_count = (await session.exec(select(func.count(ProjectField.id)).where(ProjectField.project_id == project.id))).one()
    r_count = (await session.exec(select(func.count(RegistrationRecord.id)).where(RegistrationRecord.project_id == project.id))).one()

    return ProjectRead(
        id=project.id,  # type: ignore[arg-type]
        name=project.name,
        description=project.description,
        event_name=project.event_name,
        status=project.status,  # type: ignore[arg-type]
        created_at=project.created_at,
        updated_at=project.updated_at,
        field_count=f_count,
        record_count=r_count,
    )


@router.post("/{project_id}/archive", response_model=ProjectRead)
async def archive_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Archive a project."""
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")

    project.status = "archived"
    session.add(project)
    await session.commit()
    await session.refresh(project)

    f_count = (await session.exec(select(func.count(ProjectField.id)).where(ProjectField.project_id == project.id))).one()
    r_count = (await session.exec(select(func.count(RegistrationRecord.id)).where(RegistrationRecord.project_id == project.id))).one()

    return ProjectRead(
        id=project.id,  # type: ignore[arg-type]
        name=project.name,
        description=project.description,
        event_name=project.event_name,
        status=project.status,  # type: ignore[arg-type]
        created_at=project.created_at,
        updated_at=project.updated_at,
        field_count=f_count,
        record_count=r_count,
    )


@router.post("/{project_id}/restore", response_model=ProjectRead)
async def restore_project(
    project_id: int,
    session: AsyncSession = Depends(get_session),
) -> ProjectRead:
    """Restore an archived project to active status."""
    project = await session.get(Project, project_id)
    if not project:
        raise NotFoundError(f"Project with ID {project_id} not found.")

    project.status = "active"
    session.add(project)
    await session.commit()
    await session.refresh(project)

    f_count = (await session.exec(select(func.count(ProjectField.id)).where(ProjectField.project_id == project.id))).one()
    r_count = (await session.exec(select(func.count(RegistrationRecord.id)).where(RegistrationRecord.project_id == project.id))).one()

    return ProjectRead(
        id=project.id,  # type: ignore[arg-type]
        name=project.name,
        description=project.description,
        event_name=project.event_name,
        status=project.status,  # type: ignore[arg-type]
        created_at=project.created_at,
        updated_at=project.updated_at,
        field_count=f_count,
        record_count=r_count,
    )
