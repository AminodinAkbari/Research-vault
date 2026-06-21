from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "urgent"}, headers=headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "urgent"


@pytest.mark.asyncio
async def test_create_duplicate_tag_fails(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    await client.post(f"/api/v1/projects/{project_id}/tags", json={"name": "dup"}, headers=headers)
    response = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "dup"}, headers=headers
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_same_tag_name_allowed_in_different_projects(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_a = await _make_project(client, headers, name="P1")
    project_b = await _make_project(client, headers, name="P2")

    resp_a = await client.post(
        f"/api/v1/projects/{project_a}/tags", json={"name": "shared-name"}, headers=headers
    )
    resp_b = await client.post(
        f"/api/v1/projects/{project_b}/tags", json={"name": "shared-name"}, headers=headers
    )
    assert resp_a.status_code == 201
    assert resp_b.status_code == 201


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    await client.post(f"/api/v1/projects/{project_id}/tags", json={"name": "a"}, headers=headers)
    await client.post(f"/api/v1/projects/{project_id}/tags", json={"name": "b"}, headers=headers)

    response = await client.get(f"/api/v1/projects/{project_id}/tags", headers=headers)
    assert response.status_code == 200
    assert {t["name"] for t in response.json()} == {"a", "b"}


@pytest.mark.asyncio
async def test_delete_tag(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    create_resp = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "temp"}, headers=headers
    )
    tag_id = create_resp.json()["id"]

    delete_resp = await client.delete(
        f"/api/v1/projects/{project_id}/tags/{tag_id}", headers=headers
    )
    assert delete_resp.status_code == 204

    list_resp = await client.get(f"/api/v1/projects/{project_id}/tags", headers=headers)
    assert list_resp.json() == []


@pytest.mark.asyncio
async def test_delete_unknown_tag_returns_404(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.delete(
        f"/api/v1/projects/{project_id}/tags/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_tags_require_project_ownership(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    project_id = await _make_project(client, headers_a, name="A's project")

    response = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": "intruder-tag"}, headers=headers_b
    )
    assert response.status_code == 403

    list_resp = await client.get(f"/api/v1/projects/{project_id}/tags", headers=headers_b)
    assert list_resp.status_code == 403