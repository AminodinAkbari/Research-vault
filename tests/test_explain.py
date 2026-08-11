# filename: tests/test_explain.py
from __future__ import annotations

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.services.ai import AIError


async def _make_project(client: AsyncClient, headers: dict, name: str = "Explain Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


async def _make_link(client: AsyncClient, headers: dict, project_id: str) -> str:
    with patch("app.services.link.extract_link_content.delay"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links",
            json={"url": "https://example.com/explain", "title": "Explain Article"},
            headers=headers,
        )
    return response.json()["id"]


@pytest.mark.asyncio
async def test_explain_endpoint_success(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    with patch("app.api.v1.links.call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = "This means self-attention is important."
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/explain",
            json={
                "selected_text": "attention mechanism",
                "start_offset": 50,
                "end_offset": 69
            },
            headers=headers
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["selected_text"] == "attention mechanism"
    assert data[0]["annotation"] == "This means self-attention is important."
    assert data[0]["color"] == "yellow"
    assert data[0]["start_offset"] == 50
    assert data[0]["end_offset"] == 69
    mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_explain_endpoint_ai_failure_returns_502(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    with patch("app.api.v1.links.call_ai", side_effect=AIError("Service unavailable")):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/explain",
            json={
                "selected_text": "some text",
                "start_offset": 0,
                "end_offset": 9
            },
            headers=headers
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI explanation service unavailable"


@pytest.mark.asyncio
async def test_explain_endpoint_empty_ai_response_saves_fallback(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    with patch("app.api.v1.links.call_ai", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = ""  
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/explain",
            json={
                "selected_text": "hard text",
                "start_offset": 10,
                "end_offset": 19
            },
            headers=headers
        )

    assert response.status_code == 200
    data = response.json()
    assert data[0]["annotation"] == "Could not generate explanation."


@pytest.mark.asyncio
async def test_explain_requires_project_ownership(client: AsyncClient, make_user) -> None:
    _, owner_headers = await make_user()
    _, intruder_headers = await make_user()

    project_id = await _make_project(client, owner_headers, name="Owner's Project")
    link_id = await _make_link(client, owner_headers, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/explain",
        json={"selected_text": "text", "start_offset": 0, "end_offset": 4},
        headers=intruder_headers
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_explain_unknown_link_404(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/00000000-0000-0000-0000-000000000000/explain",
        json={"selected_text": "text", "start_offset": 0, "end_offset": 4},
        headers=headers
    )
    
    assert response.status_code == 404