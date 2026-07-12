from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.note import Note
from app.models.tag import NoteTag, Tag


class NoteNotFoundError(Exception):
    """Raised when a note does not exist within the given project."""


def _note_select():
    return (
        select(Note)
        .options(selectinload(Note.tags), selectinload(Note.source_link))
        .execution_options(populate_existing=True)
    )


async def list_notes(db: AsyncSession, *, project_id: uuid.UUID) -> list[Note]:
    result = await db.execute(
        _note_select().where(Note.project_id == project_id).order_by(Note.created_at.desc())
    )
    return list(result.scalars().all())


async def get_note(db: AsyncSession, *, project_id: uuid.UUID, note_id: uuid.UUID) -> Note:
    result = await db.execute(
        _note_select().where(Note.id == note_id, Note.project_id == project_id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise NoteNotFoundError()
    return note


async def create_note(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    title: str,
    content: str = "",
    tag_ids: list[uuid.UUID] | None = None,
    source_link_id: uuid.UUID | None = None,
) -> Note:
    note = Note(
        project_id=project_id,
        title=title,
        content=content,
        source_link_id=source_link_id,
    )
    db.add(note)
    await db.flush()

    if tag_ids:
        await _replace_note_tags(db, note_id=note.id, project_id=project_id, tag_ids=tag_ids)
        await db.flush()

    return await get_note(db, project_id=project_id, note_id=note.id)


async def update_note(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    update_data: dict,
) -> Note:
    note = await get_note(db, project_id=project_id, note_id=note_id)

    tag_ids = update_data.pop("tag_ids", None)
    for field, value in update_data.items():
        setattr(note, field, value)

    if tag_ids is not None:
        await _replace_note_tags(db, note_id=note.id, project_id=project_id, tag_ids=tag_ids)

    await db.flush()
    return await get_note(db, project_id=project_id, note_id=note_id)


async def delete_note(db: AsyncSession, *, project_id: uuid.UUID, note_id: uuid.UUID) -> None:
    note = await get_note(db, project_id=project_id, note_id=note_id)
    await db.delete(note)
    await db.flush()


async def attach_tags(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> Note:
    note = await get_note(db, project_id=project_id, note_id=note_id)

    valid_tag_ids = await _valid_tag_ids(db, project_id=project_id, tag_ids=tag_ids)
    existing_result = await db.execute(select(NoteTag.tag_id).where(NoteTag.note_id == note.id))
    existing_tag_ids = set(existing_result.scalars().all())

    for tag_id in valid_tag_ids - existing_tag_ids:
        db.add(NoteTag(note_id=note.id, tag_id=tag_id))

    await db.flush()
    return await get_note(db, project_id=project_id, note_id=note_id)


async def detach_tag(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    note_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> Note:
    note = await get_note(db, project_id=project_id, note_id=note_id)
    await db.execute(
        NoteTag.__table__.delete().where(NoteTag.note_id == note.id, NoteTag.tag_id == tag_id)
    )
    await db.flush()
    return await get_note(db, project_id=project_id, note_id=note_id)


async def _valid_tag_ids(
    db: AsyncSession, *, project_id: uuid.UUID, tag_ids: list[uuid.UUID]
) -> set[uuid.UUID]:
    """Filter tag_ids down to ones that actually belong to this project."""
    if not tag_ids:
        return set()
    result = await db.execute(
        select(Tag.id).where(Tag.project_id == project_id, Tag.id.in_(tag_ids))
    )
    return set(result.scalars().all())


async def _replace_note_tags(
    db: AsyncSession, *, note_id: uuid.UUID, project_id: uuid.UUID, tag_ids: list[uuid.UUID]
) -> None:
    """Replace all of a note's tag associations with the given (project-scoped) tag_ids."""
    valid_tag_ids = await _valid_tag_ids(db, project_id=project_id, tag_ids=tag_ids)
    await db.execute(NoteTag.__table__.delete().where(NoteTag.note_id == note_id))
    for tag_id in valid_tag_ids:
        db.add(NoteTag(note_id=note_id, tag_id=tag_id))