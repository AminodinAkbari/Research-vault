from __future__ import annotations

import httpx
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.search import SearchResult

headers = {
    "User-Agent": "Mozilla/5.0 (compatible; ResearchVault/1.0; +http://localhost)",
    "Accept": "application/json",
    "X-Forwarded-For": "172.24.0.2",
    "X-Real-IP": "172.24.0.2",
}

async def search_searxng(query: str) -> list[SearchResult]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.SEARXNG_URL}/search",
                params={"q": query, "format": "json"},
                headers=headers,
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SearXNG returned an error: {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="SearXNG is unavailable.",
        ) from exc

    raw_results: list[dict] = resp.json().get("results", [])

    return [
        SearchResult(
            title=r.get("title") or "",
            url=r.get("url", ""),
            snippet=r.get("content") or "",
            engine=r.get("engine") or "",
        )
        for r in raw_results
        if r.get("url")
    ]