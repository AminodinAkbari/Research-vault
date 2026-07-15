from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.note import NoteCreate, NoteRead, NoteUpdate
from app.schemas.tag import TagAttachRequest
from app.services import note as note_service

router = APIRouter()


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Create a new note inside the current project."""
    return await note_service.create_note(
        db,
        project_id=project.id,
        title=payload.title,
        content=payload.content,
        tag_ids=payload.tag_ids,
        source_link_id=payload.source_link_id,
    )


@router.get("", response_model=list[NoteRead])
async def list_notes(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> list[NoteRead]:
    """List all notes that belong to the current project."""
    return await note_service.list_notes(db, project_id=project.id)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Get a single note by ID.

    Raises 404 NOT FOUND when the note does not exist in this project.
    """
    try:
        return await note_service.get_note(db, project_id=project.id, note_id=note_id)
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found") from exc


@router.put("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    payload: NoteUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Apply a partial update to a note.

    Raises 404 NOT FOUND when the note does not exist in this project.
    """
    try:
        return await note_service.update_note(
            db,
            project_id=project.id,
            note_id=note_id,
            update_data=payload.model_dump(exclude_unset=True),
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found") from exc


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a note by ID.

    Raises 404 NOT FOUND when the note does not exist in this project.
    """
    try:
        await note_service.delete_note(db, project_id=project.id, note_id=note_id)
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found") from exc


@router.post("/{note_id}/tags", response_model=NoteRead)
async def attach_tags(
    note_id: uuid.UUID,
    payload: TagAttachRequest,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Attach one or more tags to a note.

    Raises 404 NOT FOUND when the note does not exist in this project.
    """
    try:
        return await note_service.attach_tags(
            db, project_id=project.id, note_id=note_id, tag_ids=payload.tag_ids
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found") from exc


@router.delete("/{note_id}/tags/{tag_id}", response_model=NoteRead)
async def detach_tag(
    note_id: uuid.UUID,
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> NoteRead:
    """Detach a tag from a note.

    Raises 404 NOT FOUND when the note does not exist in this project.
    """
    try:
        return await note_service.detach_tag(
            db, project_id=project.id, note_id=note_id, tag_id=tag_id
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found") from exc
