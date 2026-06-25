from __future__ import annotations

from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str


class SearchResult(BaseModel):
    """A single result returned by SearXNG."""

    title: str
    url: str
    snippet: str = ""
    engine: str = ""