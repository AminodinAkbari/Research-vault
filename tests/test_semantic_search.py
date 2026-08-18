from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import ExtractionStatus, SavedLink
from app.schemas.collected_search import CollectedSearchResult
from app.services import semantic_search as semantic_search_service
from app.services.ai import AIError


async def _make_project(client: AsyncClient, headers: dict, name: str = "Sem Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


async def _make_note(
    client: AsyncClient, headers: dict, project_id: str, title: str, content: str = ""
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
    title: str,
    snippet: str = "",
) -> dict:
    with patch("app.services.link.extract_link_content.delay"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links",
            json={
                "url": f"https://example.com/{uuid.uuid4()}",
                "title": title,
                "snippet": snippet,
            },
            headers=headers,
        )
    assert response.status_code == 201
    return response.json()


def _candidate(result_type: str, title: str, rank: float = 1.0) -> CollectedSearchResult:
    return CollectedSearchResult(
        type=result_type,
        id=str(uuid.uuid4()),
        title=title,
        snippet=f"{title} snippet",
        rank=rank,
    )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_normalize_id_matches_dashed_and_bare_hex() -> None:
    raw = uuid.uuid4()
    assert semantic_search_service._normalize_id(str(raw)) == (
        semantic_search_service._normalize_id(raw.hex.upper())
    )


def test_reorder_applies_model_order() -> None:
    a, b, c = _candidate("note", "A"), _candidate("note", "B"), _candidate("link", "C")
    ordered = semantic_search_service._reorder([a, b, c], [c.id, a.id, b.id])
    assert [r.title for r in ordered] == ["C", "A", "B"]


def test_reorder_appends_ids_the_model_omitted() -> None:
    a, b, c = _candidate("note", "A"), _candidate("note", "B"), _candidate("link", "C")
    ordered = semantic_search_service._reorder([a, b, c], [c.id])
    assert [r.title for r in ordered] == ["C", "A", "B"]


def test_reorder_ignores_ids_the_model_invented() -> None:
    a, b = _candidate("note", "A"), _candidate("note", "B")
    ordered = semantic_search_service._reorder([a, b], [str(uuid.uuid4()), b.id])
    assert [r.title for r in ordered] == ["B", "A"]


def test_reorder_ignores_duplicate_ids() -> None:
    a, b = _candidate("note", "A"), _candidate("note", "B")
    ordered = semantic_search_service._reorder([a, b], [b.id, b.id, a.id])
    assert [r.title for r in ordered] == ["B", "A"]


def test_reorder_ignores_non_string_entries() -> None:
    a, b = _candidate("note", "A"), _candidate("note", "B")
    ordered = semantic_search_service._reorder([a, b], [42, b.id])
    assert [r.title for r in ordered] == ["B", "A"]


def test_reorder_tolerates_dash_stripped_ids_from_model() -> None:
    a, b = _candidate("note", "A"), _candidate("note", "B")
    ordered = semantic_search_service._reorder(
        [a, b], [uuid.UUID(b.id).hex, uuid.UUID(a.id).hex]
    )
    assert [r.title for r in ordered] == ["B", "A"]


def test_build_documents_includes_id_type_and_text() -> None:
    a = _candidate("note", "A")
    documents = semantic_search_service._build_documents(
        [a], {semantic_search_service._normalize_id(a.id): "note text"}
    )
    assert documents == [{"id": a.id, "type": "note", "text": "note text"}]


# ---------------------------------------------------------------------------
# Service (mocked AI, real full-text search)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_semantic_reorders_according_to_ai(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    first = await _make_note(
        client, headers, project_id, "Docker basics", "docker containers overview"
    )
    second = await _make_note(
        client, headers, project_id, "Docker advanced", "docker networking deep dive"
    )

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]
    assert len(baseline_ids) == 2

    # Ask the model for the exact reverse of the full-text order.
    reversed_ids = list(reversed(baseline_ids))

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(reversed_ids)
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="docker"
        )

    assert [r.id for r in results] == reversed_ids
    assert all(r.semantic is True for r in results)
    assert {first["title"], second["title"]} == {r.title for r in results}


@pytest.mark.asyncio
async def test_search_semantic_falls_back_to_fulltext_order_on_ai_error(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Docker basics", "docker overview")
    await _make_note(client, headers, project_id, "Docker advanced", "docker networking")

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]

    with patch("app.services.semantic_search.call_ai", side_effect=AIError("down")):
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="docker"
        )

    assert [r.id for r in results] == baseline_ids
    assert all(r.semantic is True for r in results)


@pytest.mark.asyncio
async def test_search_semantic_falls_back_on_invalid_json(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Docker basics", "docker overview")
    await _make_note(client, headers, project_id, "Docker advanced", "docker networking")

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = "I ranked them for you: the second one first."
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="docker"
        )

    assert [r.id for r in results] == baseline_ids


@pytest.mark.asyncio
async def test_search_semantic_recovers_id_array_wrapped_in_object(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    """The shared parser digs an array out of a wrapping object, so a model
    that returns {"ids": [...]} still reranks rather than falling back.
    """
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Docker basics", "docker overview")
    await _make_note(client, headers, project_id, "Docker advanced", "docker networking")

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]
    reversed_ids = list(reversed(baseline_ids))

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps({"ids": reversed_ids})
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="docker"
        )

    assert [r.id for r in results] == reversed_ids


@pytest.mark.asyncio
async def test_search_semantic_skips_ai_when_no_candidates(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Unrelated", "nothing here")

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="zzznomatchzzz"
        )

    assert results == []
    mock_ai.assert_not_called()


@pytest.mark.asyncio
async def test_search_semantic_limits_candidates_to_ten(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    for i in range(14):
        await _make_note(
            client, headers, project_id, f"Kubernetes note {i}", "kubernetes cluster"
        )

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        results = await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="kubernetes"
        )

    assert len(results) == semantic_search_service._MAX_CANDIDATES


@pytest.mark.asyncio
async def test_search_semantic_sends_note_title_and_content_to_ai(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(
        client, headers, project_id, "Docker basics", "the full note body text"
    )

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="docker"
        )

    prompt = mock_ai.call_args[0][0]
    assert "Query: docker" in prompt
    assert "Docker basics" in prompt
    assert "the full note body text" in prompt


@pytest.mark.asyncio
async def test_search_semantic_truncates_link_extracted_content(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link = await _make_link(
        client, headers, project_id, "Kubernetes guide", snippet="k8s intro"
    )

    row = await db_session.get(SavedLink, uuid.UUID(link["id"]))
    row.extracted_content = "z" * 5000
    row.extraction_status = ExtractionStatus.completed
    await db_session.flush()

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        await semantic_search_service.search_semantic(
            db_session, project_id=uuid.UUID(project_id), query="kubernetes"
        )

    prompt = mock_ai.call_args[0][0]
    assert prompt.count("z") == semantic_search_service._LINK_CONTENT_CHARS


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_semantic_endpoint_reorders_results(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Docker basics", "docker overview")
    await _make_note(client, headers, project_id, "Docker advanced", "docker networking")

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]
    reversed_ids = list(reversed(baseline_ids))

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(reversed_ids)
        response = await client.post(
            f"/api/v1/projects/{project_id}/search-semantic",
            json={"query": "docker"},
            headers=headers,
        )

    assert response.status_code == 200
    results = response.json()
    assert [r["id"] for r in results] == reversed_ids
    assert all(r["semantic"] is True for r in results)


@pytest.mark.asyncio
async def test_search_semantic_endpoint_keeps_collected_search_shape(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Neural nets", "backprop explained")

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        response = await client.post(
            f"/api/v1/projects/{project_id}/search-semantic",
            json={"query": "neural"},
            headers=headers,
        )

    assert response.status_code == 200
    result = response.json()[0]
    for key in ("type", "id", "title", "snippet", "rank", "semantic"):
        assert key in result
    assert result["type"] in ("note", "link")
    assert isinstance(result["rank"], float)


@pytest.mark.asyncio
async def test_search_semantic_endpoint_falls_back_on_ai_failure(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Docker basics", "docker overview")
    await _make_note(client, headers, project_id, "Docker advanced", "docker networking")

    baseline = await client.get(
        f"/api/v1/projects/{project_id}/search-collected",
        params={"q": "docker"},
        headers=headers,
    )
    baseline_ids = [r["id"] for r in baseline.json()]

    with patch("app.services.semantic_search.call_ai", side_effect=AIError("down")):
        response = await client.post(
            f"/api/v1/projects/{project_id}/search-semantic",
            json={"query": "docker"},
            headers=headers,
        )

    assert response.status_code == 200
    assert [r["id"] for r in response.json()] == baseline_ids


@pytest.mark.asyncio
async def test_search_semantic_endpoint_returns_both_types(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Asyncio tutorial", "asyncio basics")
    await _make_link(
        client, headers, project_id, "Asyncio docs", snippet="official asyncio docs"
    )

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        response = await client.post(
            f"/api/v1/projects/{project_id}/search-semantic",
            json={"query": "asyncio"},
            headers=headers,
        )

    assert response.status_code == 200
    assert {r["type"] for r in response.json()} == {"note", "link"}


@pytest.mark.asyncio
async def test_search_semantic_endpoint_empty_results(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    await _make_note(client, headers, project_id, "Unrelated", "nothing")

    response = await client.post(
        f"/api/v1/projects/{project_id}/search-semantic",
        json={"query": "zzznomatchzzz"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_search_semantic_endpoint_rejects_empty_query(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/search-semantic",
        json={"query": ""},
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_semantic_endpoint_requires_auth(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/search-semantic", json={"query": "docker"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_semantic_endpoint_requires_project_ownership(
    client: AsyncClient, make_user
) -> None:
    _, owner_headers = await make_user()
    _, intruder_headers = await make_user()
    project_id = await _make_project(client, owner_headers)
    await _make_note(client, owner_headers, project_id, "Private", "secret docker")

    response = await client.post(
        f"/api/v1/projects/{project_id}/search-semantic",
        json={"query": "secret"},
        headers=intruder_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_search_semantic_endpoint_scoped_to_project(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_a = await _make_project(client, headers, name="P-A")
    project_b = await _make_project(client, headers, name="P-B")
    await _make_note(client, headers, project_a, "Docker in A", "docker one")
    await _make_note(client, headers, project_b, "Docker in B", "docker two")

    with patch(
        "app.services.semantic_search.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([])
        response_a = await client.post(
            f"/api/v1/projects/{project_a}/search-semantic",
            json={"query": "docker"},
            headers=headers,
        )
        response_b = await client.post(
            f"/api/v1/projects/{project_b}/search-semantic",
            json={"query": "docker"},
            headers=headers,
        )

    titles_a = {r["title"] for r in response_a.json()}
    titles_b = {r["title"] for r in response_b.json()}
    assert titles_a == {"Docker in A"}
    assert titles_b == {"Docker in B"}
