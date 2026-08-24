from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.core.rate_limiter import ai_rate_limit
from app.db.session import get_db
from app.models.project import Project
from app.schemas.collected_search import (
    CollectedSearchResult,
    SemanticSearchRequest,
    SemanticSearchResult,
)
from app.services.collected_search import search_collected
from app.services.semantic_search import search_semantic

router = APIRouter()


@router.get("/search-collected", response_model=list[CollectedSearchResult])
async def search_collected_endpoint(
    q: str = Query(..., min_length=1, description="Full-text search query"),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[CollectedSearchResult]:
    """Search notes and saved links in the current project."""
    return await search_collected(db, project_id=project.id, q=q)


@router.post(
    "/search-semantic",
    response_model=list[SemanticSearchResult],
    dependencies=[Depends(ai_rate_limit)],
)
async def search_semantic_endpoint(
    payload: SemanticSearchRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[SemanticSearchResult]:
    """Full-text search over the project, reranked by semantic relevance.

    Always 200: when the AI reranker is unavailable the full-text ordering is
    returned unchanged, so search never breaks because the model is down.
    """
    return await search_semantic(db, project_id=project.id, query=payload.query)
