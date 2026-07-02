from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


async def _make_tag(client: AsyncClient, headers: dict, project_id: str, name: str) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/tags", json={"name": name}, headers=headers
    )
    assert response.status_code == 201
    return response.json()["id"]


async def _make_link(
    client: AsyncClient, headers: dict, project_id: str, url: str = "https://example.com"
) -> str:
    response = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": url, "title": "Example"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.asyncio
async def test_attach_tag_to_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    tag_id = await _make_tag(client, headers, project_id, "important")
    link_id = await _make_link(client, headers, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["tags"]) == 1
    assert body["tags"][0]["name"] == "important"
    assert body["tags"][0]["id"] == tag_id


@pytest.mark.asyncio
async def test_attach_multiple_tags_to_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    tag_id_a = await _make_tag(client, headers, project_id, "alpha")
    tag_id_b = await _make_tag(client, headers, project_id, "beta")
    link_id = await _make_link(client, headers, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id_a, tag_id_b]},
        headers=headers,
    )
    assert response.status_code == 200
    tag_names = {t["name"] for t in response.json()["tags"]}
    assert tag_names == {"alpha", "beta"}


@pytest.mark.asyncio
async def test_attach_tag_idempotent(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    tag_id = await _make_tag(client, headers, project_id, "dup")
    link_id = await _make_link(client, headers, project_id)

    await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )
    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )
    assert response.status_code == 200
    assert len(response.json()["tags"]) == 1


@pytest.mark.asyncio
async def test_attach_tag_from_other_project_ignored(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_a = await _make_project(client, headers, name="P-A")
    project_b = await _make_project(client, headers, name="P-B")

    foreign_tag_id = await _make_tag(client, headers, project_b, "foreign")
    link_id = await _make_link(client, headers, project_a)

    response = await client.post(
        f"/api/v1/projects/{project_a}/links/{link_id}/tags",
        json={"tag_ids": [foreign_tag_id]},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["tags"] == []


@pytest.mark.asyncio
async def test_detach_tag_from_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    tag_id = await _make_tag(client, headers, project_id, "removable")
    link_id = await _make_link(client, headers, project_id)

    await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )

    detach_resp = await client.delete(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags/{tag_id}",
        headers=headers,
    )
    assert detach_resp.status_code == 200
    assert detach_resp.json()["tags"] == []


@pytest.mark.asyncio
async def test_detach_nonexistent_tag_returns_empty(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    response = await client.delete(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["tags"] == []


@pytest.mark.asyncio
async def test_attach_tags_link_not_found(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    tag_id = await _make_tag(client, headers, project_id, "t")

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/00000000-0000-0000-0000-000000000000/tags",
        json={"tag_ids": [tag_id]},
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_link_tags_require_project_ownership(client: AsyncClient, make_user) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()

    project_id = await _make_project(client, headers_a)
    tag_id = await _make_tag(client, headers_a, project_id, "secret")
    link_id = await _make_link(client, headers_a, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/tags",
        json={"tag_ids": [tag_id]},
        headers=headers_b,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_link_tags_included_in_response(client: AsyncClient, make_user) -> None:
    """Tags on a link are always serialised in the response body."""
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    get_resp = await client.get(
        f"/api/v1/projects/{project_id}/links/{link_id}", headers=headers
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["tags"] == []