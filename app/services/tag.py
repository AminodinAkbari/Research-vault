from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.link import SavedLink
from app.models.note import Note
from app.models.tag import LinkTag, NoteTag, Tag


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


async def get_tagged_items(
    db: AsyncSession, *, project_id: uuid.UUID, tag_id: uuid.UUID
) -> tuple[list[Note], list[SavedLink]]:
    """Return all notes and saved links within a project that carry the given tag.

    Filters by project_id in addition to tag_id as defense-in-depth, even
    though a tag can only ever be attached to items within its own project.
    """
    note_result = await db.execute(
        select(Note)
        .join(NoteTag, NoteTag.note_id == Note.id)
        .where(NoteTag.tag_id == tag_id, Note.project_id == project_id)
        .options(selectinload(Note.tags))
        .order_by(Note.created_at.desc())
    )
    notes = list(note_result.scalars().all())

    link_result = await db.execute(
        select(SavedLink)
        .join(LinkTag, LinkTag.link_id == SavedLink.id)
        .where(LinkTag.tag_id == tag_id, SavedLink.project_id == project_id)
        .options(selectinload(SavedLink.tags))
        .order_by(SavedLink.created_at.desc())
    )
    links = list(link_result.scalars().all())

    return notes, links