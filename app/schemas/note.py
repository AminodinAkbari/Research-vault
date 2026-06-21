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
    """Payload for creating a note; optionally attach existing tag IDs."""

    tag_ids: list[uuid.UUID] = []


class NoteUpdate(BaseModel):
    """Partial update – all fields optional."""

    title: Optional[str] = None
    content: Optional[str] = None
    tag_ids: Optional[list[uuid.UUID]] = None


class NoteRead(NoteBase):
    """Public-facing note representation with resolved tags."""

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []

    model_config = ConfigDict(from_attributes=True)