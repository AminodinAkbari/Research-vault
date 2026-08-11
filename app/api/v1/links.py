from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.link import SavedLinkCreate, SavedLinkRead
from app.schemas.search import SearchQuery, SearchResult
from app.schemas.tag import TagAttachRequest
from app.schemas.highlights import ExplainRequest, HighlightRead
from app.services import link as link_service
from app.services import highlight as highlight_service
from app.services.searxng import search_searxng
from app.services.ai import call_ai, AIError

router = APIRouter()


@router.post("/search", response_model=list[SearchResult])
async def search(
    payload: SearchQuery,
    project: Project = Depends(get_current_project),
) -> list[SearchResult]:
    """Run an external web search using SearXNG."""
    return await search_searxng(payload.query)


@router.post("/links", response_model=SavedLinkRead, status_code=status.HTTP_201_CREATED)
async def create_link(
    payload: SavedLinkCreate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
    """Save a new link to the current project."""
    return await link_service.create_link(
        db,
        project_id=project.id,
        url=payload.url,
        title=payload.title,
        snippet=payload.snippet,
        search_query=payload.search_query,
    )


@router.get("/links", response_model=list[SavedLinkRead])
async def list_links(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[SavedLinkRead]:
    """List all saved links for the current project."""
    return await link_service.list_links(db, project_id=project.id)


@router.get("/links/{link_id}", response_model=SavedLinkRead)
async def get_link(
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
    """Get a single saved link by ID.

    Raises 404 NOT FOUND when the link does not exist in this project.
    """
    try:
        return await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc


@router.delete("/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a saved link by ID.

    Raises 404 NOT FOUND when the link does not exist in this project.
    """
    try:
        await link_service.delete_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc


@router.post("/links/{link_id}/tags", response_model=SavedLinkRead)
async def attach_tags_to_link(
    link_id: uuid.UUID,
    payload: TagAttachRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
    """Attach one or more tags to a saved link.

    Raises 404 NOT FOUND when the link does not exist in this project.
    """
    try:
        return await link_service.attach_tags(
            db, project_id=project.id, link_id=link_id, tag_ids=payload.tag_ids
        )
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc


@router.delete("/links/{link_id}/tags/{tag_id}", response_model=SavedLinkRead)
async def detach_tag_from_link(
    link_id: uuid.UUID,
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
    """Detach a tag from a saved link.

    Raises 404 NOT FOUND when the link does not exist in this project.
    """
    try:
        return await link_service.detach_tag(
            db, project_id=project.id, link_id=link_id, tag_id=tag_id
        )
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc


@router.post("/links/{link_id}/explain", response_model=list[HighlightRead])
async def explain_link_text(
    link_id: uuid.UUID,
    payload: ExplainRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[HighlightRead]:
    """Generates an AI explanation for selected text and saves it as a highlight."""
    try:
        link = await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc

    system_msg = "You are a helpful research assistant. Explain the following text in one or two concise sentences."
    try:
        explanation = await call_ai(payload.selected_text, system_prompt=system_msg)
    except AIError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI explanation service unavailable"
        )

    if not explanation:
        explanation = "Could not generate explanation."

    await highlight_service.create_highlight(
        db,
        link_id=link.id,
        selected_text=payload.selected_text,
        annotation=explanation,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        color="yellow"
    )

    return await highlight_service.list_highlights(db, link_id=link.id)