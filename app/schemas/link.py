from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.link import ExtractionStatus, ReadingStatus
from app.schemas.tag import TagResponse


class SavedLinkBase(BaseModel):
    url: str
    title: str
    snippet: str = ""
    search_query: Optional[str] = None


class SavedLinkCreate(SavedLinkBase):
    """Payload for saving a link; optionally attach existing tag IDs."""

    tag_ids: list[uuid.UUID] = []


class ManualExtractionRequest(BaseModel):
    """Payload for pasting a URL to extract directly, bypassing web search."""

    url: str

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("url must be a valid http(s) URL")
        return value


class SavedLinkUpdate(BaseModel):
    """Partial update – all fields optional."""

    title: Optional[str] = None
    snippet: Optional[str] = None
    extracted_content: Optional[str] = None
    extraction_status: Optional[ExtractionStatus] = None
    tag_ids: Optional[list[uuid.UUID]] = None
    status: Optional[ReadingStatus] = None


class SavedLinkRead(SavedLinkBase):
    """Public-facing saved link representation with resolved tags."""

    id: uuid.UUID
    project_id: uuid.UUID
    extracted_content: Optional[str] = None
    extraction_status: ExtractionStatus
    status: ReadingStatus = ReadingStatus.to_read
    created_at: datetime
    tags: list[TagResponse] = []
    summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LinkStatusUpdate(BaseModel):
    """Payload for the link reading-status PATCH endpoint."""

    status: ReadingStatus


class LinkSummaryResponse(BaseModel):
    id: uuid.UUID
    summary: str
    
class LinkStatusResponse(BaseModel):
    id: uuid.UUID
    status: ReadingStatus


class ReExtractResponse(BaseModel):
    id: uuid.UUID
    extraction_status: ExtractionStatus
    detail: str