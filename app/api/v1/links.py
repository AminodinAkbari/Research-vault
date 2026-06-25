from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.link import SavedLinkCreate, SavedLinkRead
from app.schemas.search import SearchQuery, SearchResult
from app.services import link as link_service
from app.services.searxng import search_searxng

router = APIRouter()


@router.post("/search", response_model=list[SearchResult])
async def search(
    payload: SearchQuery,
    project: Project = Depends(get_current_project),
) -> list[SearchResult]:
    return await search_searxng(payload.query)


@router.post("/links", response_model=SavedLinkRead, status_code=status.HTTP_201_CREATED)
async def create_link(
    payload: SavedLinkCreate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
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
    return await link_service.list_links(db, project_id=project.id)


@router.get("/links/{link_id}", response_model=SavedLinkRead)
async def get_link(
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> SavedLinkRead:
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
    try:
        await link_service.delete_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Link not found"
        ) from exc