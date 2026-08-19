from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import SavedLink
from app.services import link as link_service
from app.services.ai import AIError, call_ai
from app.schemas.link import LinkSummaryResponse

_SYSTEM_PROMPT = (
    "Summarise the following article in 3-5 sentences. Return only the summary text."
)

_MAX_CONTENT_CHARS = 12000

class LinkNotExtractedError(Exception):
    """Raised when a link has no extracted content to summarise yet."""
    pass

class SummarisationFailedError(Exception):
    """Raised when the upstream AI service is unreachable, errors out, or
    returns an empty summary.
    """
    pass

async def summarise_link(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    link_id: uuid.UUID,
) -> LinkSummaryResponse:
    """Summarise a saved link's extracted content and store it directly on the link.

    Raises LinkNotFoundError (from link_service) when the link isn't in this
    project, LinkNotExtractedError when extraction hasn't produced content
    yet, and SummarisationFailedError when the AI call fails.
    """
    link = await link_service.get_link(db, project_id=project_id, link_id=link_id)
    
    # Excellent optimization: Return immediately if already summarized
    if link.summary is not None:
        return link
    
    content = (link.extracted_content or "").strip()
    if not content:
        raise LinkNotExtractedError(
            "This link has no extracted content yet. Wait for extraction to "
            "complete, then try again."
        )

    try:
        summary = await call_ai(
            content[:_MAX_CONTENT_CHARS],
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.3,
        )
    except AIError as exc:
        raise SummarisationFailedError(str(exc)) from exc

    summary = summary.strip()
    if not summary:
        raise SummarisationFailedError("The AI service returned an empty summary.")

    # Save directly to the link
    link.summary = summary
    await db.flush()
    await db.refresh(link)
    
    return link