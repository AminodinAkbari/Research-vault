from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "filter-user@example.com") -> None:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret123"}
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def _create_project_via_ui(client: AsyncClient, name: str = "Filter Project") -> str:
    response = await client.post(
        "/dashboard/projects",
        data={"name": name, "description": "desc"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    api_resp = await client.get("/api/v1/projects")
    return next(p for p in api_resp.json() if p["name"] == name)["id"]


async def _create_tag(client: AsyncClient, project_id: str, name: str) -> str:
    response = await client.post(f"/api/v1/projects/{project_id}/tags", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


async def _create_note(client: AsyncClient, project_id: str, title: str) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/notes", json={"title": title}
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _create_link(client: AsyncClient, project_id: str, title: str) -> str:
    with patch("app.services.link.extract_link_content.delay"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links",
            json={"url": f"https://example.com/{title}", "title": title},
        )
    assert response.status_code == 201
    return response.json()["id"]


# ---------------------------------------------------------------------------
# Tag filtering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tag_items_ui_returns_notes_and_links(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    tag_id = await _create_tag(client, project_id, "research")
    note_id = await _create_note(client, project_id, "Tagged note")
    link_id = await _create_link(client, project_id, "Tagged link")

    await client.post(
        f"/api/v1/projects/{project_id}/notes/{note_id}/tags", json={"tag_ids": [tag_id]}
    )
    await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags", json={"tag_ids": [tag_id]}
    )

    response = await client.get(f"/projects/{project_id}/tags/{tag_id}/items")
    assert response.status_code == 200
    assert "Tagged note" in response.text
    assert "Tagged link" in response.text
    assert "Note" in response.text
    assert "Link" in response.text


@pytest.mark.asyncio
async def test_tag_items_ui_empty(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    tag_id = await _create_tag(client, project_id, "unused")

    response = await client.get(f"/projects/{project_id}/tags/{tag_id}/items")
    assert response.status_code == 200
    assert "No items tagged" in response.text


@pytest.mark.asyncio
async def test_tag_items_ui_unknown_tag_404(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.get(
        f"/projects/{project_id}/tags/00000000-0000-0000-0000-000000000000/items"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_note_tag_badges_are_clickable(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    tag_id = await _create_tag(client, project_id, "clickable")
    note_id = await _create_note(client, project_id, "Note")
    await client.post(
        f"/api/v1/projects/{project_id}/notes/{note_id}/tags", json={"tag_ids": [tag_id]}
    )

    response = await client.get(f"/projects/{project_id}/notes/list")
    assert response.status_code == 200
    assert f"/projects/{project_id}/tags/{tag_id}/items" in response.text


# ---------------------------------------------------------------------------
# Manual re-extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_link_ui_resets_status_and_queues_task(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link(client, project_id, "Extractable")

    with patch("app.services.link.extract_link_content.delay") as mock_delay:
        response = await client.post(f"/projects/{project_id}/links/{link_id}/extract")

    assert response.status_code == 200
    assert "Extracting" in response.text
    assert "disabled" in response.text
    mock_delay.assert_called_once_with(link_id)


@pytest.mark.asyncio
async def test_extract_link_ui_unknown_link_404(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)

    response = await client.post(
        f"/projects/{project_id}/links/00000000-0000-0000-0000-000000000000/extract"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_single_link_item_fragment(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link(client, project_id, "Single Item")

    response = await client.get(f"/projects/{project_id}/links/{link_id}")
    assert response.status_code == 200
    assert "Single Item" in response.text
    assert 'class="note-item"' in response.text


@pytest.mark.asyncio
async def test_extraction_ui_requires_project_ownership(client: AsyncClient) -> None:
    await _register(client, email="extract-owner@example.com")
    project_id = await _create_project_via_ui(client, name="Owner Extract Project")
    link_id = await _create_link(client, project_id, "Owned link")

    client.cookies.clear()
    await _register(client, email="extract-intruder@example.com")

    response = await client.post(f"/projects/{project_id}/links/{link_id}/extract")
    assert response.status_code == 403