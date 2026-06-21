from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag


class TagNotFoundError(Exception):
    """Raised when a tag does not exist within the given project."""


class TagAlreadyExistsError(Exception):
    """Raised when a tag name is already used within the project."""


async def list_tags(db: AsyncSession, *, project_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(select(Tag).where(Tag.project_id == project_id).order_by(Tag.name))
    return list(result.scalars().all())


async def get_tag(db: AsyncSession, *, project_id: uuid.UUID, tag_id: uuid.UUID) -> Tag:
    result = await db.execute(select(Tag).where(Tag.id == tag_id, Tag.project_id == project_id))
    tag = result.scalar_one_or_none()
    if tag is None:
        raise TagNotFoundError()
    return tag


async def create_tag(db: AsyncSession, *, project_id: uuid.UUID, name: str) -> Tag:
    existing = await db.execute(
        select(Tag).where(Tag.project_id == project_id, Tag.name == name)
    )
    if existing.scalar_one_or_none() is not None:
        raise TagAlreadyExistsError()

    tag = Tag(project_id=project_id, name=name)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    return tag


async def delete_tag(db: AsyncSession, *, project_id: uuid.UUID, tag_id: uuid.UUID) -> None:
    tag = await get_tag(db, project_id=project_id, tag_id=tag_id)
    await db.delete(tag)
    await db.flush()