from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.highlight import Highlight


class HighlightNotFoundError(Exception):
    """Raised when a highlight does not exist for the given link."""


async def list_highlights(db: AsyncSession, *, link_id: uuid.UUID) -> list[Highlight]:
    result = await db.execute(
        select(Highlight)
        .where(Highlight.link_id == link_id)
        .order_by(Highlight.created_at.asc())
    )
    return list(result.scalars().all())


async def create_highlight(
    db: AsyncSession,
    *,
    link_id: uuid.UUID,
    selected_text: str,
    annotation: str | None = None,
    start_offset: int = 0,
    end_offset: int = 0,
) -> Highlight:
    highlight = Highlight(
        link_id=link_id,
        selected_text=selected_text,
        annotation=annotation,
        start_offset=start_offset,
        end_offset=end_offset,
    )
    db.add(highlight)
    await db.flush()
    await db.refresh(highlight)
    return highlight


async def delete_highlight(
    db: AsyncSession, *, link_id: uuid.UUID, highlight_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Highlight).where(Highlight.id == highlight_id, Highlight.link_id == link_id)
    )
    highlight = result.scalar_one_or_none()
    if highlight is None:
        raise HighlightNotFoundError()
    await db.delete(highlight)
    await db.flush()