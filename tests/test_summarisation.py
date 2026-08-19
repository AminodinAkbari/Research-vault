# filename: tests/test_summarisation.py
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import ExtractionStatus, SavedLink
from app.services import summarisation as summarisation_service
from app.services.ai import AIError

FIXED_SUMMARY = (
    "The article explains transformers. It covers self-attention. "
    "It compares them to RNNs. It closes with applications."
)


async def _make_project(client: AsyncClient, headers: dict, name: str = "Sum Project") -> str:
    response = await client.post("/api/v1/projects", json={"name": name}, headers=headers)
    return response.json()["id"]


async def _make_link(
    client: AsyncClient,
    headers: dict,
    project_id: str,
    title: str = "Transformers Explained",
) -> str:
    with patch("app.services.link.extract_link_content.delay"):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links",
            json={"url": "https://example.com/transformers", "title": title},
            headers=headers,
        )
    assert response.status_code == 201
    return response.json()["id"]


async def _mark_extracted(
    db: AsyncSession, link_id: str, content: str = "A long article about transformers."
) -> None:
    """Simulate a finished extraction. There's no public API to set extracted
    content (it's written by the Celery task), so the row is updated directly.
    """
    link = await db.get(SavedLink, uuid.UUID(link_id))
    link.extracted_content = content
    link.extraction_status = ExtractionStatus.completed
    await db.flush()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summarise_link_updates_saved_link_summary(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = FIXED_SUMMARY
        link = await summarisation_service.summarise_link(
            db_session,
            project_id=uuid.UUID(project_id),
            link_id=uuid.UUID(link_id),
        )

    assert link.summary == FIXED_SUMMARY
    assert str(link.id) == link_id
    mock_ai.assert_called_once()


@pytest.mark.asyncio
async def test_summarise_link_uses_cached_summary(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    # Manually set a summary to test the early-return optimization
    link = await db_session.get(SavedLink, uuid.UUID(link_id))
    link.summary = "Existing summary."
    await db_session.flush()

    with patch("app.services.summarisation.call_ai", new_callable=AsyncMock) as mock_ai:
        updated_link = await summarisation_service.summarise_link(
            db_session,
            project_id=uuid.UUID(project_id),
            link_id=uuid.UUID(link_id),
        )

    assert updated_link.summary == "Existing summary."
    mock_ai.assert_not_called()  # Should bypass AI completely


@pytest.mark.asyncio
async def test_summarise_link_sends_extracted_content_as_user_prompt(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id, content="The full article body.")

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = FIXED_SUMMARY
        await summarisation_service.summarise_link(
            db_session,
            project_id=uuid.UUID(project_id),
            link_id=uuid.UUID(link_id),
        )

    args, kwargs = mock_ai.call_args
    assert args[0] == "The full article body."
    assert kwargs["system_prompt"] == summarisation_service._SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_summarise_link_truncates_very_long_content(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id, content="y" * 50_000)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = FIXED_SUMMARY
        await summarisation_service.summarise_link(
            db_session,
            project_id=uuid.UUID(project_id),
            link_id=uuid.UUID(link_id),
        )

    assert len(mock_ai.call_args[0][0]) == summarisation_service._MAX_CONTENT_CHARS


@pytest.mark.asyncio
async def test_summarise_link_raises_when_not_extracted(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        with pytest.raises(summarisation_service.LinkNotExtractedError):
            await summarisation_service.summarise_link(
                db_session,
                project_id=uuid.UUID(project_id),
                link_id=uuid.UUID(link_id),
            )

    mock_ai.assert_not_called()


@pytest.mark.asyncio
async def test_summarise_link_raises_on_ai_error(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch("app.services.summarisation.call_ai", side_effect=AIError("down")):
        with pytest.raises(summarisation_service.SummarisationFailedError):
            await summarisation_service.summarise_link(
                db_session,
                project_id=uuid.UUID(project_id),
                link_id=uuid.UUID(link_id),
            )


@pytest.mark.asyncio
async def test_summarise_link_raises_on_empty_summary(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = "   "
        with pytest.raises(summarisation_service.SummarisationFailedError):
            await summarisation_service.summarise_link(
                db_session,
                project_id=uuid.UUID(project_id),
                link_id=uuid.UUID(link_id),
            )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summarise_endpoint_returns_updated_link(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = FIXED_SUMMARY
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/summarise",
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == FIXED_SUMMARY
    assert body["id"] == link_id


@pytest.mark.asyncio
async def test_summarise_endpoint_persists_summary_on_link(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch(
        "app.services.summarisation.call_ai", new_callable=AsyncMock
    ) as mock_ai:
        mock_ai.return_value = FIXED_SUMMARY
        await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/summarise",
            headers=headers,
        )

    # Check persistence directly in the SavedLink table
    link = await db_session.get(SavedLink, uuid.UUID(link_id))
    assert link.summary == FIXED_SUMMARY

    # And verify it shows up through the normal links listing endpoint
    listing = await client.get(
        f"/api/v1/projects/{project_id}/links", headers=headers
    )
    assert any(l["id"] == link_id and l["summary"] == FIXED_SUMMARY for l in listing.json())


@pytest.mark.asyncio
async def test_summarise_endpoint_400_when_not_extracted(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/summarise",
        headers=headers,
    )

    assert response.status_code == 400
    assert "extracted content" in response.json()["detail"]


@pytest.mark.asyncio
async def test_summarise_endpoint_502_on_ai_failure(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)
    await _mark_extracted(db_session, link_id)

    with patch("app.services.summarisation.call_ai", side_effect=AIError("down")):
        response = await client.post(
            f"/api/v1/projects/{project_id}/links/{link_id}/summarise",
            headers=headers,
        )

    assert response.status_code == 502
    assert response.json()["detail"] == "Summarisation service unavailable"


@pytest.mark.asyncio
async def test_summarise_endpoint_404_for_unknown_link(
    client: AsyncClient, make_user
) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/"
        "00000000-0000-0000-0000-000000000000/summarise",
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_summarise_endpoint_requires_auth(client: AsyncClient, make_user) -> None:
    _, headers = await make_user()
    project_id = await _make_project(client, headers)
    link_id = await _make_link(client, headers, project_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/summarise"
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_summarise_endpoint_requires_project_ownership(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    _, owner_headers = await make_user()
    _, intruder_headers = await make_user()
    project_id = await _make_project(client, owner_headers)
    link_id = await _make_link(client, owner_headers, project_id)
    await _mark_extracted(db_session, link_id)

    response = await client.post(
        f"/api/v1/projects/{project_id}/links/{link_id}/summarise",
        headers=intruder_headers,
    )
    assert response.status_code == 403