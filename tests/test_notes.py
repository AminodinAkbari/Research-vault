from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_note(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={"title": "Note 1", "content": "Hello"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Note 1"
    assert body["content"] == "Hello"
    assert body["tags"] == []


@pytest.mark.asyncio
async def test_list_notes(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    await client.post(f"/api/v1/projects/{project_id}/notes", json={"title": "N1"}, headers=headers)
    await client.post(f"/api/v1/projects/{project_id}/notes", json={"title": "N2"}, headers=headers)

    response = await client.get(f"/api/v1/projects/{project_id}/notes", headers=headers)
    assert response.status_code == 200
    assert {n["title"] for n in response.json()} == {"N1", "N2"}


@pytest.mark.asyncio
async def test_get_update_delete_note(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes", json={"title": "Original"}, headers=headers
    )
    note_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/projects/{project_id}/notes/{note_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Original"

    update_resp = await client.put(
        f"/api/v1/projects/{project_id}/notes/{note_id}",
        json={"title": "Updated"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated"

    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}/notes/{note_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    missing_resp = await client.get(
        f"/api/v1/projects/{project_id}/notes/{note_id}", headers=headers
    )
    assert missing_resp.status_code == 404


@pytest.mark.asyncio
async def test_notes_require_project_ownership(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    project_id = await _make_project(client, headers_a, name="A's project")

    # User B cannot list or create notes in A's project.
    list_resp = await client.get(f"/api/v1/projects/{project_id}/notes", headers=headers_b)
    assert list_resp.status_code == 403

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes", json={"title": "Intruder"}, headers=headers_b
    )
    assert create_resp.status_code == 403


@pytest.mark.asyncio
async def test_notes_require_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.get(f"/api/v1/projects/{project_id}/notes")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_note_with_tags(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    tag_resp = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "important"}, headers=headers
    )
    tag_id = tag_resp.json()["id"]

    note_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={"title": "Tagged note", "tag_ids": [tag_id]},
        headers=headers,
    )
    assert note_resp.status_code == 201
    tags = note_resp.json()["tags"]
    assert len(tags) == 1
    assert tags[0]["name"] == "important"


@pytest.mark.asyncio
async def test_attach_and_detach_tag(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    tag_resp = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "research"}, headers=headers
    )
    tag_id = tag_resp.json()["id"]

    note_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes", json={"title": "Plain note"}, headers=headers
    )
    note_id = note_resp.json()["id"]
    assert note_resp.json()["tags"] == []

    attach_resp = await client.post(
        f"/api/v1/projects/{project_id}/notes/{note_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )
    assert attach_resp.status_code == 200
    assert len(attach_resp.json()["tags"]) == 1

    detach_resp = await client.delete(
        f"/api/v1/projects/{project_id}/notes/{note_id}/tags/{tag_id}", headers=headers
    )
    assert detach_resp.status_code == 200
    assert detach_resp.json()["tags"] == []