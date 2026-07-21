from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str = "highlight-user@example.com") -> None:
    response = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "supersecret123"}
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


async def _create_project_via_ui(client: AsyncClient, name: str = "Highlight Project") -> str:
    response = await client.post(
        "/dashboard/projects",
        data={"name": name, "description": "desc"},
        headers={"HX-Request": "true"},
    )
    assert response.status_code == 200
    api_resp = await client.get("/api/v1/projects")
    return next(p for p in api_resp.json() if p["name"] == name)["id"]


async def _create_link_via_api(client: AsyncClient, project_id: str) -> str:
    with patch("app.services.link.extract_link_content.delay"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links",
            json={"url": "https://example.com/article", "title": "Article"},
        )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_highlight_via_ui(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link_via_api(client, project_id)

    response = await client.post(
        f"/projects/{project_id}/links/{link_id}/highlights",
        data={
            "selected_text": "an important passage",
            "annotation": "worth remembering",
            "start_offset": "10",
            "end_offset": "31",
        },
    )
    assert response.status_code == 200
    assert "an important passage" in response.text
    assert "worth remembering" in response.text


@pytest.mark.asyncio
async def test_highlights_shown_on_reader_page(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link_via_api(client, project_id)

    await client.post(
        f"/projects/{project_id}/links/{link_id}/highlights",
        data={"selected_text": "quoted text", "annotation": "", "start_offset": "0", "end_offset": "11"},
    )

    response = await client.get(f"/projects/{project_id}/links/{link_id}/read")
    assert response.status_code == 200
    assert "quoted text" in response.text


@pytest.mark.asyncio
async def test_delete_highlight_via_ui(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link_via_api(client, project_id)

    create_resp = await client.post(
        f"/projects/{project_id}/links/{link_id}/highlights",
        data={"selected_text": "removable highlight", "annotation": "", "start_offset": "0", "end_offset": "19"},
    )
    assert "removable highlight" in create_resp.text

    reader_resp = await client.get(f"/projects/{project_id}/links/{link_id}/read")
    assert "highlight-" in reader_resp.text
    highlight_id = reader_resp.text.split('id="highlight-')[1].split('"')[0]

    delete_resp = await client.delete(
        f"/projects/{project_id}/links/{link_id}/highlights/{highlight_id}"
    )
    assert delete_resp.status_code == 200
    assert delete_resp.text == ""

    reader_resp_after = await client.get(f"/projects/{project_id}/links/{link_id}/read")
    assert "removable highlight" not in reader_resp_after.text


@pytest.mark.asyncio
async def test_delete_unknown_highlight_returns_404(client: AsyncClient) -> None:
    await _register(client)
    project_id = await _create_project_via_ui(client)
    link_id = await _create_link_via_api(client, project_id)

    response = await client.delete(
        f"/projects/{project_id}/links/{link_id}/highlights/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_highlights_require_project_ownership(client: AsyncClient) -> None:
    await _register(client, email="highlight-owner@example.com")
    project_id = await _create_project_via_ui(client, name="Owner Highlight Project")
    link_id = await _create_link_via_api(client, project_id)

    client.cookies.clear()
    await _register(client, email="highlight-intruder@example.com")

    response = await client.post(
        f"/projects/{project_id}/links/{link_id}/highlights",
        data={"selected_text": "x", "annotation": "", "start_offset": "0", "end_offset": "1"},
    )
    assert response.status_code == 403