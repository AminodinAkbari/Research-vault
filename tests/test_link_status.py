"""Tests for the reading-list status feature on saved links.

Mock-based: the database session and auth dependencies are replaced with
mocks and the link service is patched, so no database is involved. Ownership
behaviour is exercised through the real `get_current_project` dependency
with only its project-service call mocked.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.link import ExtractionStatus, ReadingStatus, SavedLink
from app.services import link as link_service
from app.services import project as project_service

PROJECT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


@pytest.fixture(autouse=True)
def owned_project_mock():
    """Patch only the project lookup inside the real get_current_project
    dependency, so its 403/404 translation logic is genuinely exercised."""
    with patch(
        "app.services.project.get_owned_project", new_callable=AsyncMock
    ) as mock:
        mock.return_value = SimpleNamespace(
            id=PROJECT_ID, user_id=USER_ID, name="Project", description=""
        )
        yield mock


@pytest.fixture
async def client():
    """ASGI client with the DB session and current-user dependencies mocked."""

    async def _override_get_db():
        yield AsyncMock()

    async def _override_user():
        return SimpleNamespace(id=USER_ID, email="owner@example.com")

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _fake_link(link_id: uuid.UUID | None = None, status: str = "to_read") -> SimpleNamespace:
    return SimpleNamespace(
        id=link_id or uuid.uuid4(),
        project_id=PROJECT_ID,
        url="https://example.com",
        title="Example",
        snippet="",
        search_query=None,
        extracted_content=None,
        extraction_status=ExtractionStatus.pending,
        status=status,
        created_at=datetime.now(timezone.utc),
        tags=[],
        summary=None,
    )


# ---------------------------------------------------------------------------
# Default status
# ---------------------------------------------------------------------------


def test_status_column_defaults_to_to_read() -> None:
    """The model-level default for SavedLink.status is to_read, so newly
    created links enter the reading list in that state."""
    column = SavedLink.__table__.columns["status"]
    assert column.default.arg == ReadingStatus.to_read.value
    assert column.server_default.arg == ReadingStatus.to_read.value


@pytest.mark.asyncio
async def test_created_link_response_includes_default_status(
    client: AsyncClient,
) -> None:
    with patch("app.services.link.create_link", new_callable=AsyncMock) as create_mock:
        create_mock.return_value = _fake_link(status=ReadingStatus.to_read.value)
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/links",
            json={"url": "https://example.com", "title": "Example"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "to_read"


# ---------------------------------------------------------------------------
# PATCH status endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_link_status_returns_updated_link(client: AsyncClient) -> None:
    link_id = uuid.uuid4()
    with patch(
        "app.services.link.set_link_status", new_callable=AsyncMock
    ) as set_mock:
        set_mock.return_value = _fake_link(link_id=link_id, status="reading")
        response = await client.patch(
            f"/api/v1/projects/{PROJECT_ID}/links/{link_id}/status",
            json={"status": "reading"},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(link_id)
    assert body["status"] == "reading"

    assert set_mock.await_count == 1
    kwargs = set_mock.await_args.kwargs
    assert kwargs["project_id"] == PROJECT_ID
    assert kwargs["link_id"] == link_id
    assert kwargs["status"] == "reading"


@pytest.mark.asyncio
async def test_update_link_status_invalid_value_returns_422(
    client: AsyncClient,
) -> None:
    link_id = uuid.uuid4()
    with patch(
        "app.services.link.set_link_status", new_callable=AsyncMock
    ) as set_mock:
        response = await client.patch(
            f"/api/v1/projects/{PROJECT_ID}/links/{link_id}/status",
            json={"status": "skimming"},
        )
    assert response.status_code == 422
    set_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_link_status_not_found(client: AsyncClient) -> None:
    link_id = uuid.uuid4()
    with patch(
        "app.services.link.set_link_status", new_callable=AsyncMock
    ) as set_mock:
        set_mock.side_effect = link_service.LinkNotFoundError
        response = await client.patch(
            f"/api/v1/projects/{PROJECT_ID}/links/{link_id}/status",
            json={"status": "done"},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_link_status_other_users_project_returns_403(
    client: AsyncClient,
) -> None:
    link_id = uuid.uuid4()
    with patch(
        "app.services.link.set_link_status", new_callable=AsyncMock
    ) as set_mock, patch(
        "app.services.project.get_owned_project", new_callable=AsyncMock
    ) as project_mock:
        project_mock.side_effect = project_service.ProjectForbiddenError
        response = await client.patch(
            f"/api/v1/projects/{PROJECT_ID}/links/{link_id}/status",
            json={"status": "done"},
        )
    assert response.status_code == 403
    set_mock.assert_not_awaited()


# ---------------------------------------------------------------------------
# Status filtering on the list endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_links_passes_status_filter(client: AsyncClient) -> None:
    reading_link = _fake_link(status="reading")
    with patch("app.services.link.list_links", new_callable=AsyncMock) as list_mock:
        list_mock.return_value = [reading_link]
        response = await client.get(
            f"/api/v1/projects/{PROJECT_ID}/links", params={"status": "reading"}
        )

    assert response.status_code == 200, response.text
    links = response.json()
    assert len(links) == 1
    assert links[0]["status"] == "reading"
    assert list_mock.await_args.kwargs["status"] == "reading"


@pytest.mark.asyncio
async def test_list_links_without_status_passes_none(client: AsyncClient) -> None:
    with patch("app.services.link.list_links", new_callable=AsyncMock) as list_mock:
        list_mock.return_value = []
        response = await client.get(f"/api/v1/projects/{PROJECT_ID}/links")

    assert response.status_code == 200
    assert list_mock.await_args.kwargs["status"] is None


@pytest.mark.asyncio
async def test_list_links_invalid_status_returns_422(client: AsyncClient) -> None:
    with patch("app.services.link.list_links", new_callable=AsyncMock) as list_mock:
        response = await client.get(
            f"/api/v1/projects/{PROJECT_ID}/links", params={"status": "later"}
        )
    assert response.status_code == 422
    list_mock.assert_not_awaited()
