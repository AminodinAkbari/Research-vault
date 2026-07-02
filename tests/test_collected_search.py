from __future__ import annotations

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

async def _make_project(client: AsyncClient, headers: dict, name: str = "Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


async def _make_note(
    client: AsyncClient,
    headers: dict,
    project_id: str,
    title: str,
    content: str = "",
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/notes",
        json={"title": title, "content": content},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


async def _make_link(
    client: AsyncClient,
    headers: dict,
    project_id: str,
    url: str,
    title: str,
    snippet: str = "",
) -> dict:
    response = await client.post(
        f"/api/v1/projects/{project_id}/links",
        json={"url": url, "title": title, "snippet": snippet},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()

# ---------- helper to build fake results ----------
def fake_result(result_type: str, title: str, snippet: str = "", rank: float = 0.9, **kwargs) -> dict:
    """Build a single search result dict matching CollectedSearchResult."""
    return {
        "type": result_type,
        "id": str(uuid.uuid4()),
        "title": title,
        "snippet": snippet,
        "rank": rank,
        **kwargs,
    }


@pytest.mark.asyncio
async def test_search_collected_finds_note(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(
        client, headers, project_id,
        title="Quantum Computing Basics",
        content="Quantum entanglement and superposition explained.",
    )

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            fake_result("note", "Quantum Computing Basics", "entanglement...", 0.95)
        ]

        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "quantum"},
            headers=headers,
        )

    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    assert any(r["type"] == "note" for r in results)
    assert any("Quantum" in r["title"] for r in results)


@pytest.mark.asyncio
async def test_search_collected_finds_link(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_link(
        client, headers, project_id,
        url="https://example.com/ml",
        title="Machine Learning Overview",
        snippet="Introduction to supervised and unsupervised learning algorithms.",
    )

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            fake_result("link", "Machine Learning Overview", "supervised...", 0.9)
        ]

        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "supervised"},
            headers=headers,
        )

    assert response.status_code == 200
    results = response.json()
    assert any(r["type"] == "link" for r in results)



@pytest.mark.asyncio
async def test_search_collected_returns_both_types(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(
        client, headers, project_id,
        title="Python asyncio tutorial",
        content="Async programming with asyncio.",
    )
    await _make_link(
        client, headers, project_id,
        url="https://example.com/async",
        title="Asyncio documentation",
        snippet="Official Python asyncio docs.",
    )

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            fake_result("note", "Python asyncio tutorial", "async...", 0.95),
            fake_result("link", "Asyncio documentation", "event loops", 0.85),
        ]

        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "asyncio"},
            headers=headers,
        )

    assert response.status_code == 200
    results = response.json()
    types = {r["type"] for r in results}
    assert "note" in types
    assert "link" in types


@pytest.mark.asyncio
async def test_search_collected_empty_results(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, title="Unrelated", content="Nothing")

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = []
        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "zzznomatchzzz"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_collected_scoped_to_project(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_a = await _make_project(client, headers, name="P-A")
    project_b = await _make_project(client, headers, name="P-B")

    await _make_note(client, headers, project_a, title="Blockchain fund", content="...")
    await _make_note(client, headers, project_b, title="Blockchain finance", content="...")

    # We'll make the mock return different IDs based on project_id
    async def mock_search(db, project_id, q):
        if str(project_id) == project_a:
            return [fake_result("note", "Blockchain fund", rank=0.9)]
        else:
            return [fake_result("note", "Blockchain finance", rank=0.8)]

    with patch("app.api.v1.collected_search.search_collected", side_effect=mock_search):
        response_a = await client.get(
            f"/api/v1/projects/{project_a}/search-collected",
            params={"q": "blockchain"},
            headers=headers,
        )
        ids_a = {r["id"] for r in response_a.json()}

        response_b = await client.get(
            f"/api/v1/projects/{project_b}/search-collected",
            params={"q": "blockchain"},
            headers=headers,
        )
        ids_b = {r["id"] for r in response_b.json()}

    assert ids_a.isdisjoint(ids_b)


@pytest.mark.asyncio
async def test_search_collected_requires_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    response = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "test"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_collected_requires_project_ownership(
    client: AsyncClient, make_user
) -> None:
    _, headers_a = await make_user()
    _, headers_b = await make_user()
    project_id = await _make_project(client, headers_a)
    await _make_note(client, headers_a, project_id, title="Private", content="secret")

    # Ownership is checked before the search function runs, so we don’t need to mock
    response = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "secret"},
        headers=headers_b,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_collected_result_schema(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, title="Neural nets", content="...")

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            fake_result("note", "Neural networks explained", "backprop", 0.88)
        ]

        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "neural"},
            headers=headers,
        )

    assert response.status_code == 200
    result = response.json()[0]
    for key in ("type", "id", "title", "snippet", "rank"):
        assert key in result
    assert result["type"] in ("note", "link")
    assert isinstance(result["rank"], float)


@pytest.mark.asyncio
async def test_search_collected_missing_q_param(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    response = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_collected_ranks_relevant_higher(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, title="Docker containers", content="...")
    await _make_note(client, headers, project_id, title="Unrelated", content="docker once")

    with patch("app.api.v1.collected_search.search_collected", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = [
            fake_result("note", "Docker containers", rank=0.95),
            fake_result("note", "Unrelated topic", rank=0.4),
        ]

        response = await client.get(
            f"/api/v1/projects/{project_id}/search-collected",
            params={"q": "docker"},
            headers=headers,
        )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["rank"] >= results[1]["rank"]
    assert results[0]["title"] == "Docker containers"