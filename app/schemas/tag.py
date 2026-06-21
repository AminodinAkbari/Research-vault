from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    """Payload for creating a tag within a project."""


class TagUpdate(BaseModel):
    """Partial update – all fields optional."""

    name: Optional[str] = None


class TagRead(TagBase):
    """Full tag representation, used for the tags list/detail endpoints."""

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagResponse(BaseModel):
    """Lightweight tag representation embedded inside note/link responses."""

    id: uuid.UUID
    name: str

    model_config = ConfigDict(from_attributes=True)


class TagAttachRequest(BaseModel):
    """Payload for attaching one or more tags to a note."""

    tag_ids: list[uuid.UUID]