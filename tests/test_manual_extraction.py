from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_manual_extract_creates_link_and_queues_task(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    with patch("app.api.v1.links.extract_link_content.delay") as mock_delay:
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/manual-extract",
            json={"url": "https://arxiv.org/abs/1706.03762"},
            headers=headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://arxiv.org/abs/1706.03762"
    assert body["title"] == "arxiv.org/abs/1706.03762"
    assert body["extraction_status"] == "pending"
    assert body["search_query"] is None
    assert body["tags"] == []
    mock_delay.assert_called_once_with(body["id"])


@pytest.mark.asyncio
async def test_manual_extract_invalid_url_returns_422(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/manual-extract",
        json={"url": "not-a-url"},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_manual_extract_requires_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    client.cookies.clear()
    response = await client.post(
        f"/api/v1/projects/{project_id}/links/manual-extract",
        json={"url": "https://example.com"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_manual_extract_requires_project_ownership(
    client: AsyncClient, make_user
) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()
    project_id = await _make_project(client, headers_a, name="A's project")

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/manual-extract",
        json={"url": "https://example.com"},
        headers=headers_b,
    )
    assert response.status_code == 403
