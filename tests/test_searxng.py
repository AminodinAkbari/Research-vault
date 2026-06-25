from __future__ import annotations

from unittest.mock import ANY, AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


SEARXNG_RESPONSE = {
    "results": [
        {"title": "Result 1", "url": "https://example.com/1", "content": "Snippet 1", "engine": "google"},
        {"title": "Result 2", "url": "https://example.com/2", "content": "Snippet 2", "engine": "bing"},
    ]
}


@pytest.mark.asyncio
async def test_search(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    with patch("app.api.v1.links.search_searxng", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            {"title": "Result 1", "url": "https://example.com/1", "snippet": "Snippet 1", "engine": "google"},
            {"title": "Result 2", "url": "https://example.com/2", "snippet": "Snippet 2", "engine": "bing"},
        ]

        response = await client.post(
            f"/api/v1/projects/{project_id}/search",
            json={"query": "test query"},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["title"] == "Result 1"
    assert body[0]["url"] == "https://example.com/1"
    assert body[1]["engine"] == "bing"


@pytest.mark.asyncio
async def test_search_requires_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/search",
        json={"query": "test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_requires_project_ownership(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    project_id = await _make_project(client, headers_a, name="A's project")

    response = await client.post(
        f"/api/v1/projects/{project_id}/search",
        json={"query": "test"},
        headers=headers_b,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_empty_results(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    with patch("app.api.v1.links.search_searxng", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []

        response = await client.post(
            f"/api/v1/projects/{project_id}/search",
            json={"query": "nothing"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == []
