from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.link import ExtractionStatus, SavedLink
from app.models.tag import LinkTag, Tag
from app.tasks.extraction import extract_link_content


class LinkNotFoundError(Exception):
    """Raised when a link does not exist within the given project."""


def _link_select():
    return (
        select(SavedLink)
        .options(selectinload(SavedLink.tags))
        .execution_options(populate_existing=True)
    )


async def list_links(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    status: Optional[str] = None,
) -> list[SavedLink]:
    query = _link_select().where(SavedLink.project_id == project_id)
    if status is not None:
        query = query.where(SavedLink.status == status)
    result = await db.execute(query.order_by(SavedLink.created_at.desc()))
    return list(result.scalars().all())


async def get_link(
    db: AsyncSession, *, project_id: uuid.UUID, link_id: uuid.UUID
) -> SavedLink:
    result = await db.execute(
        _link_select().where(SavedLink.id == link_id, SavedLink.project_id == project_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise LinkNotFoundError()
    return link


async def create_link(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    url: str,
    title: str,
    snippet: str = "",
    search_query: Optional[str] = None,
) -> SavedLink:
    link = SavedLink(
        project_id=project_id,
        url=url,
        title=title,
        snippet=snippet,
        search_query=search_query,
        extraction_status=ExtractionStatus.pending,
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    extract_link_content.delay(str(link.id))
    return await get_link(db, project_id=project_id, link_id=link.id)


async def delete_link(
    db: AsyncSession, *, project_id: uuid.UUID, link_id: uuid.UUID
) -> None:
    link = await get_link(db, project_id=project_id, link_id=link_id)
    await db.delete(link)
    await db.flush()


async def set_link_status(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    link_id: uuid.UUID,
    status: str,
) -> SavedLink:
    """Update a link's reading-list status and return the refreshed link."""
    link = await get_link(db, project_id=project_id, link_id=link_id)
    link.status = status
    await db.flush()
    return await get_link(db, project_id=project_id, link_id=link.id)


async def trigger_extraction(
    db: AsyncSession, *, project_id: uuid.UUID, link_id: uuid.UUID
) -> SavedLink:
    """Reset a link's extraction status to pending and re-queue the Celery
    extraction task. Used for manual re-extraction (e.g. after a failure, or
    to refresh already-completed content).
    """
    link = await get_link(db, project_id=project_id, link_id=link_id)
    link.extraction_status = ExtractionStatus.pending
    await db.flush()
    extract_link_content.delay(str(link.id))
    return await get_link(db, project_id=project_id, link_id=link_id)


async def attach_tags(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    link_id: uuid.UUID,
    tag_ids: list[uuid.UUID],
) -> SavedLink:
    link = await get_link(db, project_id=project_id, link_id=link_id)

    valid_tag_ids = await _valid_tag_ids(db, project_id=project_id, tag_ids=tag_ids)
    existing_result = await db.execute(
        select(LinkTag.tag_id).where(LinkTag.link_id == link.id)
    )
    existing_tag_ids = set(existing_result.scalars().all())

    for tag_id in valid_tag_ids - existing_tag_ids:
        db.add(LinkTag(link_id=link.id, tag_id=tag_id))

    await db.flush()
    return await get_link(db, project_id=project_id, link_id=link.id)


async def detach_tag(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    link_id: uuid.UUID,
    tag_id: uuid.UUID,
) -> SavedLink:
    link = await get_link(db, project_id=project_id, link_id=link_id)
    await db.execute(
        LinkTag.__table__.delete().where(
            LinkTag.link_id == link.id, LinkTag.tag_id == tag_id
        )
    )
    await db.flush()
    return await get_link(db, project_id=project_id, link_id=link.id)


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