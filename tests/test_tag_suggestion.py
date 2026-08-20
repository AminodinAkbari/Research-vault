# filename: tests/test_tag_suggestion.py
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services import tag_suggestion as tag_suggestion_service
from app.services.ai import AIError


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_filter_suggestions_drops_unknown_tags() -> None:
    result = tag_suggestion_service._filter_suggestions(
        ["python", "invented-tag", "async"], ["python", "async", "docker"]
    )
    assert result == ["python", "async"]


def test_filter_suggestions_is_case_insensitive_but_returns_project_spelling() -> None:
    result = tag_suggestion_service._filter_suggestions(
        ["PYTHON", "  AsyncIO "], ["python", "asyncio"]
    )
    assert result == ["python", "asyncio"]


def test_filter_suggestions_collapses_duplicates() -> None:
    result = tag_suggestion_service._filter_suggestions(
        ["python", "Python", "python"], ["python", "async"]
    )
    assert result == ["python"]


def test_filter_suggestions_caps_at_three() -> None:
    result = tag_suggestion_service._filter_suggestions(
        ["a", "b", "c", "d", "e"], ["a", "b", "c", "d", "e"]
    )
    assert result == ["a", "b", "c"]


def test_filter_suggestions_preserves_model_order() -> None:
    result = tag_suggestion_service._filter_suggestions(
        ["docker", "python"], ["python", "async", "docker"]
    )
    assert result == ["docker", "python"]


def test_build_user_prompt_includes_type_tags_and_content() -> None:
    # Passed "My Title" as the new first argument
    prompt = tag_suggestion_service._build_user_prompt(
        "My Title", "Some article body", "link", ["python", "docker"]
    )
    assert "link" in prompt
    assert "python" in prompt
    assert "Some article body" in prompt
    assert "My Title" in prompt


def test_build_user_prompt_truncates_long_content() -> None:
    content = "x" * 20_000
    # Passed None for title
    prompt = tag_suggestion_service._build_user_prompt(None, content, "note", ["a"])
    # Extract just the content block to check the length
    body = prompt.split("Content:\n", 1)[1].split("\n\nAvailable tags:", 1)[0]
    assert len(body) == tag_suggestion_service._MAX_CONTENT_CHARS


# ---------------------------------------------------------------------------
# Service logic (mocked AI)
# ---------------------------------------------------------------------------


async def _project_with_tags(
    client: AsyncClient, headers: dict, tag_names: list[str]
) -> str:
    response = await client.post(
        "/api/v1/projects", json={"name": "Suggest Project"}, headers=headers
    )
    project_id = response.json()["id"]
    for name in tag_names:
        created = await client.post(
            f"/api/v1/projects/{project_id}/tags", json={"name": name}, headers=headers
        )
        assert created.status_code == 201
    return project_id


@pytest.mark.asyncio
async def test_suggest_tags_returns_filtered_subset(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python", "asyncio"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(["python", "javascript", "asyncio"])
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            title="Async programming",
            content="An article about async python",
            content_type="note",
        )

    assert suggested == ["python", "asyncio"]
    mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_suggest_tags_skips_ai_when_project_has_no_tags(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, [])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == []
    mock_ai.assert_not_called()


@pytest.mark.asyncio
async def test_suggest_tags_skips_ai_for_blank_content(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            title="   ",
            content="   ",
            content_type="note",
        )

    assert suggested == []
    mock_ai.assert_not_called()


@pytest.mark.asyncio
async def test_suggest_tags_returns_empty_on_ai_error(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", side_effect=AIError("down")
    ):
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == []


@pytest.mark.asyncio
async def test_suggest_tags_returns_empty_on_invalid_json(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = "I think python would be a good tag!"
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == []


@pytest.mark.asyncio
async def test_suggest_tags_recovers_array_wrapped_in_object(
    client: AsyncClient, make_user, db_session
) -> None:
    """A model that wraps the array in an object is still usable — the shared
    parser digs the array out rather than discarding the response.
    """
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps({"tags": ["python"]})
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == ["python"]


@pytest.mark.asyncio
async def test_suggest_tags_returns_empty_for_object_without_array(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps({"tag": "python"})
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == []


@pytest.mark.asyncio
async def test_suggest_tags_drops_non_string_entries(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps([1, {"name": "python"}, "python"])
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == ["python"]


@pytest.mark.asyncio
async def test_suggest_tags_accepts_markdown_fenced_array(
    client: AsyncClient, make_user, db_session
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = 'Sure!\n```json\n["python"]\n```'
        suggested = await tag_suggestion_service.suggest_tags(
            db_session,
            project_id=uuid.UUID(project_id),
            content="Some content",
            content_type="note",
        )

    assert suggested == ["python"]


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_filters_to_existing_tags(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python", "docker"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(["docker", "kubernetes", "python"])
        response = await client.post(
            f"/api/v1/projects/{project_id}/suggest-tags",
            json={"title": "DevOps", "content": "Running python in containers", "content_type": "note"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {"suggested_tags": ["docker", "python"]}


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_accepts_link_content_type(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(["python"])
        response = await client.post(
            f"/api/v1/projects/{project_id}/suggest-tags",
            json={"content": "An article", "content_type": "link"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["suggested_tags"] == ["python"]


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_returns_200_with_empty_list_on_ai_failure(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", side_effect=AIError("unavailable")
    ):
        response = await client.post(
            f"/api/v1/projects/{project_id}/suggest-tags",
            json={"content": "Some content", "content_type": "note"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {"suggested_tags": []}


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_returns_200_on_invalid_json(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = "not json"
        response = await client.post(
            f"/api/v1/projects/{project_id}/suggest-tags",
            json={"content": "Some content", "content_type": "note"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json() == {"suggested_tags": []}


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_accepts_arbitrary_content_type(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(["python"])
        response = await client.post(
            f"/api/v1/projects/{project_id}/suggest-tags",
            json={"content": "Some content", "content_type": "highlight"},
            headers=headers,
        )
    # Verifies graceful processing of unexpected string types rather than a strict 422
    assert response.status_code == 200
    assert response.json() == {"suggested_tags": ["python"]}


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_gracefully_handles_empty_content(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    response = await client.post(
        f"/api/v1/projects/{project_id}/suggest-tags",
        json={"title": "", "content": "", "content_type": "note"},
        headers=headers,
    )
    # The service layer catches the empty content and returns an empty list safely
    assert response.status_code == 200
    assert response.json() == {"suggested_tags": []}


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_requires_auth(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _project_with_tags(client, headers, ["python"])

    response = await client.post(
        f"/api/v1/projects/{project_id}/suggest-tags",
        json={"content": "Some content", "content_type": "note"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_requires_project_ownership(
    client: AsyncClient, make_user
) -> None:
    _, owner_headers = await make_user()
    _, intruder_headers = await make_user()
    project_id = await _project_with_tags(client, owner_headers, ["python"])

    response = await client.post(
        f"/api/v1/projects/{project_id}/suggest-tags",
        json={"content": "Some content", "content_type": "note"},
        headers=intruder_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_suggest_tags_endpoint_does_not_leak_other_projects_tags(
    client: AsyncClient, make_user
) -> None:
    """A tag that exists only in another project must be filtered out."""
    _, headers = await make_user()
    project_a = await _project_with_tags(client, headers, ["python"])
    await _project_with_tags(client, headers, ["rust"])

    with patch(
        "app.services.tag_suggestion.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = json.dumps(["rust", "python"])
        response = await client.post(
            f"/api/v1/projects/{project_a}/suggest-tags",
            json={"content": "Systems programming", "content_type": "note"},
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["suggested_tags"] == ["python"]