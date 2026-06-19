from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Payload for creating a project."""


class ProjectUpdate(BaseModel):
    """Partial update – all fields optional."""

    name: Optional[str] = None
    description: Optional[str] = None


class ProjectRead(ProjectBase):
    """Public-facing project representation."""

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
