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
    """Public-facing tag representation."""

    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
