from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.tag import TagResponse


class NoteBase(BaseModel):
    title: str
    content: str = ""


class NoteCreate(NoteBase):
    """Payload for creating a note; optionally attach existing tag IDs and a source link."""

    tag_ids: list[uuid.UUID] = []
    source_link_id: Optional[uuid.UUID] = None


class NoteUpdate(BaseModel):
    """Partial update – all fields optional."""

    title: Optional[str] = None
    content: Optional[str] = None
    tag_ids: Optional[list[uuid.UUID]] = None
    source_link_id: Optional[uuid.UUID] = None


class NoteRead(NoteBase):
    """Public-facing note representation with resolved tags."""

    id: uuid.UUID
    project_id: uuid.UUID
    source_link_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)