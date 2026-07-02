from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CollectedSearchResult(BaseModel):
    """A single result from the unified full-text search across notes and links."""

    type: Literal["note", "link"]
    id: str
    title: str
    snippet: str
    rank: float