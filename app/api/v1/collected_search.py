from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.collected_search import CollectedSearchResult
from app.services.collected_search import search_collected

router = APIRouter()


@router.get("/search-collected", response_model=list[CollectedSearchResult])
async def search_collected_endpoint(
    q: str = Query(..., min_length=1, description="Full-text search query"),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[CollectedSearchResult]:
    """Search notes and saved links in the current project."""
    return await search_collected(db, project_id=project.id, q=q)
