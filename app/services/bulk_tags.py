from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import SavedLink
from app.models.note import Note
from app.models.tag import LinkTag, NoteTag, Tag


class BulkTagsItemNotFoundError(Exception):
    """Raised when an item (note or link) is missing from the project."""


class BulkTagsTagNotFoundError(Exception):
    """Raised when a tag is missing from the project."""


async def bulk_apply_tags(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    item_type: str,
    item_ids: list[uuid.UUID],
    action: str,
    tag_ids: list[uuid.UUID],
) -> tuple[list[uuid.UUID], list[uuid.UUID]]:
    """Add or remove tag associations across multiple notes or links,
    idempotently. Returns (updated_item_ids, applied_tag_ids).

    Raises BulkTagsItemNotFoundError / BulkTagsTagNotFoundError when any of
    the referenced IDs do not belong to the given project.
    """
    unique_item_ids = list(dict.fromkeys(item_ids))
    unique_tag_ids = list(dict.fromkeys(tag_ids))

    await _ensure_tags_exist(db, project_id=project_id, tag_ids=unique_tag_ids)

    if item_type == "notes":
        await _ensure_items_exist(
            db, model=Note, project_id=project_id, item_ids=unique_item_ids
        )
        if action == "add":
            await _add_note_tags(db, note_ids=unique_item_ids, tag_ids=unique_tag_ids)
        else:
            await _remove_note_tags(db, note_ids=unique_item_ids, tag_ids=unique_tag_ids)
    else:
        await _ensure_items_exist(
            db, model=SavedLink, project_id=project_id, item_ids=unique_item_ids
        )
        if action == "add":
            await _add_link_tags(db, link_ids=unique_item_ids, tag_ids=unique_tag_ids)
        else:
            await _remove_link_tags(db, link_ids=unique_item_ids, tag_ids=unique_tag_ids)

    await db.flush()
    return unique_item_ids, unique_tag_ids


async def _ensure_items_exist(
    db: AsyncSession, *, model, project_id: uuid.UUID, item_ids: list[uuid.UUID]
) -> None:
    result = await db.execute(
        select(model.id).where(model.project_id == project_id, model.id.in_(item_ids))
    )
    found = set(result.scalars().all())
    if found != set(item_ids):
        raise BulkTagsItemNotFoundError()


async def _ensure_tags_exist(
    db: AsyncSession, *, project_id: uuid.UUID, tag_ids: list[uuid.UUID]
) -> None:
    print(project_id)
    print(tag_ids)
    result = await db.execute(
        select(Tag.id).where(Tag.project_id == project_id, Tag.id.in_(tag_ids))
    )
    found = set(result.scalars().all())
    if found != set(tag_ids):
        raise BulkTagsTagNotFoundError()


async def _add_note_tags(
    db: AsyncSession, *, note_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]
) -> None:
    existing = await db.execute(
        select(NoteTag.note_id, NoteTag.tag_id).where(
            NoteTag.note_id.in_(note_ids), NoteTag.tag_id.in_(tag_ids)
        )
    )
    existing_pairs = set(existing.all())
    for note_id in note_ids:
        for tag_id in tag_ids:
            if (note_id, tag_id) not in existing_pairs:
                db.add(NoteTag(note_id=note_id, tag_id=tag_id))


async def _remove_note_tags(
    db: AsyncSession, *, note_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]
) -> None:
    await db.execute(
        NoteTag.__table__.delete().where(
            NoteTag.note_id.in_(note_ids), NoteTag.tag_id.in_(tag_ids)
        )
    )


async def _add_link_tags(
    db: AsyncSession, *, link_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]
) -> None:
    existing = await db.execute(
        select(LinkTag.link_id, LinkTag.tag_id).where(
            LinkTag.link_id.in_(link_ids), LinkTag.tag_id.in_(tag_ids)
        )
    )
    existing_pairs = set(existing.all())
    for link_id in link_ids:
        for tag_id in tag_ids:
            if (link_id, tag_id) not in existing_pairs:
                db.add(LinkTag(link_id=link_id, tag_id=tag_id))


async def _remove_link_tags(
    db: AsyncSession, *, link_ids: list[uuid.UUID], tag_ids: list[uuid.UUID]
) -> None:
    await db.execute(
        LinkTag.__table__.delete().where(
            LinkTag.link_id.in_(link_ids), LinkTag.tag_id.in_(tag_ids)
        )
    )
