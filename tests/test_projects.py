from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    response = await client.post(
        "/api/v1/projects", json={"name": "My Research", "description": "desc"}, headers=headers
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "My Research"
    assert body["description"] == "desc"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_projects_scoped_to_user(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    await client.post("/api/v1/projects", json={"name": "A1"}, headers=headers_a)
    await client.post("/api/v1/projects", json={"name": "A2"}, headers=headers_a)
    await client.post("/api/v1/projects", json={"name": "B1"}, headers=headers_b)

    response_a = await client.get("/api/v1/projects", headers=headers_a)
    assert response_a.status_code == 200
    assert {p["name"] for p in response_a.json()} == {"A1", "A2"}

    response_b = await client.get("/api/v1/projects", headers=headers_b)
    assert {p["name"] for p in response_b.json()} == {"B1"}


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    create_resp = await client.post("/api/v1/projects", json={"name": "P1"}, headers=headers)
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == project_id


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_project_forbidden_for_other_user(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    create_resp = await client.post(
        "/api/v1/projects", json={"name": "A's project"}, headers=headers_a
    )
    project_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/projects/{project_id}", headers=headers_b)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    create_resp = await client.post("/api/v1/projects", json={"name": "Old"}, headers=headers)
    project_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/projects/{project_id}", json={"name": "New"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New"


@pytest.mark.asyncio
async def test_update_project_forbidden_for_other_user(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    create_resp = await client.post(
        "/api/v1/projects", json={"name": "A's project"}, headers=headers_a
    )
    project_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/projects/{project_id}", json={"name": "Hacked"}, headers=headers_b
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    create_resp = await client.post("/api/v1/projects", json={"name": "ToDelete"}, headers=headers)
    project_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/projects/{project_id}", headers=headers)
    assert response.status_code == 204

    get_resp = await client.get(f"/api/v1/projects/{project_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_project_forbidden_for_other_user(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    create_resp = await client.post(
        "/api/v1/projects", json={"name": "A's project"}, headers=headers_a
    )
    project_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/projects/{project_id}", headers=headers_b)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_projects_require_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/projects")
    assert response.status_code == 401