from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.tag import TagCreate, TagRead
from app.services import tag as tag_service

router = APIRouter()


@router.post("", response_model=TagRead, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: TagCreate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> TagRead:
    """Create a new tag for the current project.

    Raises 409 CONFLICT if a tag with the same name already exists.
    """
    try:
        return await tag_service.create_tag(db, project_id=project.id, name=payload.name)
    except tag_service.TagAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this name already exists in this project",
        ) from exc


@router.get("", response_model=list[TagRead])
async def list_tags(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[TagRead]:
    """List all tags defined for the current project."""
    return await tag_service.list_tags(db, project_id=project.id)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tag by ID.

    Raises 404 NOT FOUND when the tag does not exist in this project.
    """
    try:
        await tag_service.delete_tag(db, project_id=project.id, tag_id=tag_id)
    except tag_service.TagNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found") from exc
