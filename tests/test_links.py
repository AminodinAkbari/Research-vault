from __future__ import annotations

from unittest.mock import ANY

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://example.com", "title": "Example", "snippet": "An example site"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["url"] == "https://example.com"
    assert body["title"] == "Example"
    assert body["snippet"] == "An example site"
    assert body["extraction_status"] == "pending"
    assert body["tags"] == []


@pytest.mark.asyncio
async def test_list_links(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://a.com", "title": "A"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://b.com", "title": "B"},
        headers=headers,
    )

    # Last posts requests create items in list, so the links in this indent is not empty.
    response = await client.get(f"/api/v1/projects/{project_id}/links", headers=headers)
    assert response.status_code == 200
    assert {l["url"] for l in response.json()} == {"https://a.com", "https://b.com"}
    
@pytest.mark.asyncio
async def test_list_links_empty(client: AsyncClient, make_user) -> None:
    # No post method request, so we haven't any item in response array.
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    # No links created – list should be empty
    response = await client.get(f"/api/v1/projects/{project_id}/links", headers=headers)
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_get_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://example.com", "title": "Example"},
        headers=headers,
    )
    link_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/projects/{project_id}/links/{link_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["url"] == "https://example.com"
    assert get_resp.json()["title"] == "Example"


@pytest.mark.asyncio
async def test_get_unknown_link_returns_404(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.get(
        f"/api/v1/projects/{project_id}/links/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://example.com", "title": "Example"},
        headers=headers,
    )
    link_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}/links/{link_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/projects/{project_id}/links", headers=headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_unknown_link_returns_404(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.delete(
        f"/api/v1/projects/{project_id}/links/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_links_require_project_ownership(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    project_id = await _make_project(client, headers_a, name="A's project")

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": "https://example.com", "title": "Intruder"},
        headers=headers_b,
    )
    assert create_resp.status_code == 403

    list_resp = await client.get(f"/api/v1/projects/{project_id}/links", headers=headers_b)
    assert list_resp.status_code == 403


@pytest.mark.asyncio
async def test_links_require_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.get(f"/api/v1/projects/{project_id}/links")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_link_with_search_query(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={
            "url": "https://example.com",
            "title": "Example",
            "search_query": "test query",
        },
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["search_query"] == "test query"
