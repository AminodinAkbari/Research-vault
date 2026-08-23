from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.link import SavedLinkCreate, SavedLinkRead, LinkSummaryResponse, LinkStatusUpdate, LinkStatusResponse
from app.schemas.bulk_tags import BulkTagsRequest, BulkTagsResponse
from app.services import bulk_tags as bulk_tags_service
from app.schemas.search import SearchQuery, SearchResult
from app.schemas.tag import TagAttachRequest
from app.schemas.highlights import ExplainRequest, HighlightRead
from app.models.link import ReadingStatus
from app.services import link as link_service
from app.services import highlight as highlight_service
from app.services import summarisation as summarisation_service
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
    status_filter: str | None = Query(default=None, alias="status"),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[SavedLinkRead]:
    """List saved links for the current project, optionally filtered by
    reading-list status (to_read, reading, done, archived)."""
    if status_filter is not None:
        try:
            status_filter = ReadingStatus(status_filter).value
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status; must be one of: {', '.join(s.value for s in ReadingStatus)}",
            ) from exc
    return await link_service.list_links(
        db, project_id=project.id, status=status_filter
    )


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

@router.post("/links/{link_id}/summarise", response_model=LinkSummaryResponse)
async def summarise_link_endpoint(
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> LinkSummaryResponse:
    """Summarise a link's extracted content and save the summary to the link.

    Raises 404 when the link isn't in this project, 400 when extraction hasn't
    produced any content yet, and 502 when the AI service is unavailable.
    """
    try:
        return await summarisation_service.summarise_link(
            db, project_id=project.id, link_id=link_id
        )
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc
    except summarisation_service.LinkNotExtractedError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except summarisation_service.SummarisationFailedError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Summarisation service unavailable",
        ) from exc


@router.patch("/links/{link_id}/status", response_model=LinkStatusResponse)
async def update_link_status(
    link_id: uuid.UUID,
    payload: LinkStatusUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
    """Update a saved link's reading-list status.

    Raises 404 NOT FOUND when the link does not exist in this project;
    422 UNPROCESSABLE ENTITY for a status outside the allowed values.
    """
    try:
        return await link_service.set_link_status(
            db,
            project_id=project.id,
            link_id=link_id,
            status=payload.status.value,
        )
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc


@router.post("/bulk-tags", response_model=BulkTagsResponse)
async def bulk_tags(
    payload: BulkTagsRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> BulkTagsResponse:
    """Add or remove one or more tags across multiple notes or links in a
    single request. Idempotent: existing attachments are ignored on add and
    missing ones on remove.

    Raises 404 NOT FOUND when any item or tag is missing from this project;
    422 UNPROCESSABLE ENTITY for invalid enum values.
    """
    try:
        updated_items, applied_tags = await bulk_tags_service.bulk_apply_tags(
            db,
            project_id=project.id,
            item_type=payload.item_type.value,
            item_ids=payload.item_ids,
            action=payload.action.value,
            tag_ids=payload.tag_ids,
        )
    except (
        bulk_tags_service.BulkTagsItemNotFoundError,
        bulk_tags_service.BulkTagsTagNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item or tag not found"
        ) from exc
    return BulkTagsResponse(
        updated_items=updated_items,
        applied_tags=applied_tags,
        action=payload.action,
    )