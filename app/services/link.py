from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.link import ExtractionStatus, SavedLink
from app.tasks.extraction import extract_link_content


class LinkNotFoundError(Exception):
    """Raised when a link does not exist within the given project."""


def _link_select():
    return (
        select(SavedLink)
        .options(selectinload(SavedLink.tags))
        .execution_options(populate_existing=True)
    )


async def list_links(db: AsyncSession, *, project_id: uuid.UUID) -> list[SavedLink]:
    result = await db.execute(
        _link_select()
        .where(SavedLink.project_id == project_id)
        .order_by(SavedLink.created_at.desc())
    )
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