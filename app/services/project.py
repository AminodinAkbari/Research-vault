from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectNotFoundError(Exception):
    """Raised when a project does not exist."""


class ProjectForbiddenError(Exception):
    """Raised when a project exists but does not belong to the requesting user."""


async def list_projects(db: AsyncSession, *, user_id: uuid.UUID) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.user_id == user_id).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


async def get_owned_project(
    db: AsyncSession, *, project_id: uuid.UUID, user_id: uuid.UUID
) -> Project:
    """Fetch a project and verify ownership.

    Raises ProjectNotFoundError if it doesn't exist at all, ProjectForbiddenError
    if it exists but belongs to a different user.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise ProjectNotFoundError()
    if project.user_id != user_id:
        raise ProjectForbiddenError()
    return project


async def create_project(
    db: AsyncSession, *, user_id: uuid.UUID, name: str, description: str | None = None
) -> Project:
    project = Project(user_id=user_id, name=name, description=description)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def apply_project_update(
    db: AsyncSession, *, project: Project, update_data: dict
) -> Project:
    """Apply a partial update to an already-fetched, ownership-verified project."""
    for field, value in update_data.items():
        setattr(project, field, value)
    await db.flush()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, *, project: Project) -> None:
    """Delete an already-fetched, ownership-verified project (cascades to notes/links/tags)."""
    await db.delete(project)
    await db.flush()