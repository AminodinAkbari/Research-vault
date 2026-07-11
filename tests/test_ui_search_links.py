from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "ui-search@example.com") -> str:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret123"},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    # API routes require an Authorization Bearer header, while UI routes use
    # the httpOnly cookie set above. Persist the token so callers can mix both
    # kinds of endpoints with the same AsyncClient instance.
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def _create_project_via_ui(client: AsyncClient, name: str = "Search Project") -> str:
    response = await client.post(
        "/dashboard/projects",
        data={"name": name, "description": "desc"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    api_resp = await client.get("/api/v1/projects")
    project = next(p for p in api_resp.json() if p["name"] == name)
    return project["id"]


MOCK_SEARCH_RESULTS = [
    {"title": "Result One", "url": "https://example.com/1", "snippet": "First snippet", "engine": "google"},
    {"title": "Result Two", "url": "https://example.com/2", "snippet": "Second snippet", "engine": "bing"},
]


# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_web_search_ui_returns_results(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    with patch("app.api.ui_project.search_searxng", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = MOCK_SEARCH_RESULTS
        response = await client.post(
            f"/projects/{project_id}/search/web", data={"query": "test query"}
        )

    assert response.status_code == 200
    assert "Result One" in response.text
    assert "Result Two" in response.text
    assert 'name="url" value="https://example.com/1"' in response.text
    mock_search.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_web_search_ui_no_results(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    with patch("app.api.ui_project.search_searxng", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        response = await client.post(
            f"/projects/{project_id}/search/web", data={"query": "nothing found"}
        )

    assert response.status_code == 200
    assert "No results" in response.text


@pytest.mark.asyncio
async def test_web_search_ui_handles_upstream_error(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    with patch("app.api.ui_project.search_searxng", new_callable=AsyncMock) as mock_search:
        mock_search.side_effect = HTTPException(status_code=502, detail="SearXNG is unavailable.")
        response = await client.post(
            f"/projects/{project_id}/search/web", data={"query": "test"}
        )

    assert response.status_code == 200
    assert "SearXNG is unavailable." in response.text


# ---------------------------------------------------------------------------
# Saving a search result as a link
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_link_via_ui(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.post(
        f"/projects/{project_id}/links/save",
        data={
            "url": "https://example.com/article",
            "title": "Great Article",
            "snippet": "An interesting read",
            "search_query": "great articles",
        },
    )
    assert response.status_code == 200
    assert "Saved" in response.text

    api_resp = await client.get(f"/api/v1/projects/{project_id}/links")
    urls = {l["url"] for l in api_resp.json()}
    assert "https://example.com/article" in urls


# ---------------------------------------------------------------------------
# Saved links list / content / delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_links_list_fragment_empty(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.get(f"/projects/{project_id}/links/list")
    assert response.status_code == 200
    assert "No links saved yet" in response.text


@pytest.mark.asyncio
async def test_links_list_fragment_shows_saved_link(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    await client.post(
        f"/projects/{project_id}/links/save",
        data={"url": "https://example.com/x", "title": "Link X", "snippet": "", "search_query": ""},
    )

    response = await client.get(f"/projects/{project_id}/links/list")
    assert response.status_code == 200
    assert "Link X" in response.text
    assert "Pending" in response.text


@pytest.mark.asyncio
async def test_link_content_fragment_when_not_yet_extracted(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    save_resp = await client.post(
        f"/projects/{project_id}/links/save",
        data={"url": "https://example.com/y", "title": "Link Y", "snippet": "", "search_query": ""},
    )
    assert save_resp.status_code == 200

    api_resp = await client.get(f"/api/v1/projects/{project_id}/links")
    link_id = api_resp.json()[0]["id"]

    response = await client.get(f"/projects/{project_id}/links/{link_id}/content")
    assert response.status_code == 200
    assert "No extracted content available" in response.text


@pytest.mark.asyncio
async def test_link_content_fragment_unknown_link_404(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.get(
        f"/projects/{project_id}/links/00000000-0000-0000-0000-000000000000/content"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_link_via_ui(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    await client.post(
        f"/projects/{project_id}/links/save",
        data={"url": "https://example.com/z", "title": "Link Z", "snippet": "", "search_query": ""},
    )
    api_resp = await client.get(f"/api/v1/projects/{project_id}/links")
    link_id = api_resp.json()[0]["id"]

    response = await client.delete(f"/projects/{project_id}/links/{link_id}")
    assert response.status_code == 200
    assert response.text == ""

    get_resp = await client.get(f"/api/v1/projects/{project_id}/links/{link_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_unknown_link_via_ui_404(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.delete(
        f"/projects/{project_id}/links/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Full-text collected search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collected_search_ui_finds_note(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={"title": "Distributed systems", "content": "Consensus algorithms like Raft and Paxos."},
    )

    response = await client.get(
        f"/projects/{project_id}/search/collected", params={"q": "Consensus"}
    )
    assert response.status_code == 200
    assert "Distributed systems" in response.text
    assert "Note" in response.text


@pytest.mark.asyncio
async def test_collected_search_ui_no_results(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={"title": "Some note", "content": "Nothing relevant."},
    )

    response = await client.get(
        f"/projects/{project_id}/search/collected", params={"q": "zzznomatchzzz"}
    )
    assert response.status_code == 200
    assert "No matches found" in response.text


@pytest.mark.asyncio
async def test_collected_search_ui_empty_query_shows_nothing(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.get(f"/projects/{project_id}/search/collected", params={"q": ""})
    assert response.status_code == 200
    assert "No matches found" not in response.text
    assert response.text.strip() == ""


# ---------------------------------------------------------------------------
# Ownership enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_links_ui_requires_project_ownership(client: AsyncClient) -> None:
    await _register(client, email="owner2@example.com")
    project_id = await _create_project_via_ui(client, name="Owner2 Project")

    client.cookies.clear()
    await _register(client, email="intruder2@example.com")

    response = await client.get(f"/projects/{project_id}/links/list")
    assert response.status_code == 403

    response = await client.post(
        f"/projects/{project_id}/search/web", data={"query": "x"}
    )
    assert response.status_code == 403