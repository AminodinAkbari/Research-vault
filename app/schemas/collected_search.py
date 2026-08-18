from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CollectedSearchResult(BaseModel):
    """A single result from the unified full-text search across notes and links."""

    type: Literal["note", "link"]
    id: str
    title: str
    snippet: str
    rank: float


class SemanticSearchRequest(BaseModel):
    """Payload for POST /projects/{project_id}/search-semantic."""

    query: str = Field(..., min_length=1)


class SemanticSearchResult(CollectedSearchResult):
    """A full-text search result that went through AI reranking.

    Same shape as CollectedSearchResult plus a `semantic` flag, so existing
    clients of the full-text response can consume this without changes.
    `semantic` is True even when reranking fell back to full-text order — it
    marks the endpoint, not whether the model happened to succeed.
    """

    semantic: bool = True
