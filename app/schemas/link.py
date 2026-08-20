from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.link import ExtractionStatus
from app.schemas.tag import TagResponse


class SavedLinkBase(BaseModel):
    url: str
    title: str
    snippet: str = ""
    search_query: Optional[str] = None


class SavedLinkCreate(SavedLinkBase):
    """Payload for saving a link; optionally attach existing tag IDs."""

    tag_ids: list[uuid.UUID] = []


class SavedLinkUpdate(BaseModel):
    """Partial update – all fields optional."""

    title: Optional[str] = None
    snippet: Optional[str] = None
    extracted_content: Optional[str] = None
    extraction_status: Optional[ExtractionStatus] = None
    tag_ids: Optional[list[uuid.UUID]] = None


class SavedLinkRead(SavedLinkBase):
    """Public-facing saved link representation with resolved tags."""

    id: uuid.UUID
    project_id: uuid.UUID
    extracted_content: Optional[str] = None
    extraction_status: ExtractionStatus
    created_at: datetime
    tags: list[TagResponse] = []
    summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LinkSummaryResponse(BaseModel): 
    id: uuid.UUID
    summary: str