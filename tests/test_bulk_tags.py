"""Tests for the bulk-tags endpoint and service.

These are mock-based tests: the database session and auth dependencies are
replaced with mocks and the service layer is patched, so no database is
involved. Ownership behaviour is exercised through the real
`get_current_project` dependency with only its project-service call mocked.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.tag import NoteTag
from app.services import bulk_tags as bulk_tags_service
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


def _bulk_payload(**overrides) -> dict:
    payload = {
        "item_type": "notes",
        "item_ids": [str(uuid.uuid4())],
        "action": "add",
        "tag_ids": [str(uuid.uuid4())],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Endpoint tests (service layer mocked)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bulk_add_tags_returns_result(client: AsyncClient) -> None:
    note_ids = [uuid.uuid4(), uuid.uuid4()]
    tag_ids = [uuid.uuid4(), uuid.uuid4()]

    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        apply_mock.return_value = (note_ids, tag_ids)
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags",
            json=_bulk_payload(
                item_ids=[str(i) for i in note_ids], tag_ids=[str(t) for t in tag_ids]
            ),
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert sorted(data["updated_items"]) == sorted(str(i) for i in note_ids)
    assert sorted(data["applied_tags"]) == sorted(str(t) for t in tag_ids)
    assert data["action"] == "add"

    assert apply_mock.await_count == 1
    kwargs = apply_mock.await_args.kwargs
    assert kwargs["project_id"] == PROJECT_ID
    assert kwargs["item_type"] == "notes"
    assert kwargs["item_ids"] == note_ids
    assert kwargs["action"] == "add"
    assert kwargs["tag_ids"] == tag_ids


@pytest.mark.asyncio
async def test_bulk_remove_tags_returns_result(client: AsyncClient) -> None:
    link_ids = [uuid.uuid4()]
    tag_ids = [uuid.uuid4()]

    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        apply_mock.return_value = (link_ids, tag_ids)
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags",
            json=_bulk_payload(
                item_type="links",
                item_ids=[str(i) for i in link_ids],
                action="remove",
                tag_ids=[str(t) for t in tag_ids],
            ),
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["updated_items"] == [str(link_ids[0])]
    assert data["applied_tags"] == [str(tag_ids[0])]
    assert data["action"] == "remove"
    assert apply_mock.await_args.kwargs["action"] == "remove"


@pytest.mark.asyncio
async def test_bulk_tags_invalid_action_returns_422(client: AsyncClient) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags",
            json=_bulk_payload(action="explode"),
        )
    assert response.status_code == 422
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_tags_invalid_item_type_returns_422(client: AsyncClient) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags",
            json=_bulk_payload(item_type="documents"),
        )
    assert response.status_code == 422
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["item_ids", "tag_ids"])
async def test_bulk_tags_empty_id_list_returns_422(
    client: AsyncClient, field: str
) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags",
            json=_bulk_payload(**{field: []}),
        )
    assert response.status_code == 422
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_tags_unknown_item_returns_404(client: AsyncClient) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        apply_mock.side_effect = bulk_tags_service.BulkTagsItemNotFoundError
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags", json=_bulk_payload()
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bulk_tags_unknown_tag_returns_404(client: AsyncClient) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock:
        apply_mock.side_effect = bulk_tags_service.BulkTagsTagNotFoundError
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags", json=_bulk_payload()
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_bulk_tags_other_users_project_returns_403(client: AsyncClient) -> None:
    with patch(
        "app.services.bulk_tags.bulk_apply_tags", new_callable=AsyncMock
    ) as apply_mock, patch(
        "app.services.project.get_owned_project", new_callable=AsyncMock
    ) as project_mock:
        project_mock.side_effect = project_service.ProjectForbiddenError
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags", json=_bulk_payload()
        )
    assert response.status_code == 403
    apply_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_tags_missing_project_returns_404(client: AsyncClient) -> None:
    with patch(
        "app.services.project.get_owned_project", new_callable=AsyncMock
    ) as project_mock:
        project_mock.side_effect = project_service.ProjectNotFoundError
        response = await client.post(
            f"/api/v1/projects/{PROJECT_ID}/bulk-tags", json=_bulk_payload()
        )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Service unit tests (AsyncSession mocked)
# ---------------------------------------------------------------------------


def _scalar_result(rows: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def _mock_db(execute_results: list) -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=execute_results)
    db.add = MagicMock()
    return db


@pytest.mark.asyncio
async def test_bulk_apply_adds_missing_note_tag_pairs_only() -> None:
    note_ids = [uuid.uuid4(), uuid.uuid4()]
    tag_ids = [uuid.uuid4(), uuid.uuid4()]
    existing_pair = (note_ids[0], tag_ids[0])

    db = _mock_db(
        [
            _scalar_result(tag_ids),        # tag existence check
            _scalar_result(note_ids),       # note existence check
            MagicMock(all=MagicMock(return_value=[existing_pair])),  # existing pairs
        ]
    )

    updated_items, applied_tags = await bulk_tags_service.bulk_apply_tags(
        db,
        project_id=PROJECT_ID,
        item_type="notes",
        item_ids=note_ids,
        action="add",
        tag_ids=tag_ids,
    )

    db.flush.assert_awaited_once()
    added_pairs = {tuple(call.args[0].__dict__[k] for k in ("note_id", "tag_id")) for call in db.add.call_args_list}

    assert updated_items == note_ids
    assert applied_tags == tag_ids
    assert db.add.call_count == 3
    expected = {
        (note_ids[0], tag_ids[1]),
        (note_ids[1], tag_ids[0]),
        (note_ids[1], tag_ids[1]),
    }
    assert added_pairs == expected
    for association in db.add.call_args_list:
        assert isinstance(association.args[0], NoteTag)


@pytest.mark.asyncio
async def test_bulk_apply_deduplicates_ids_in_request() -> None:
    note_id = uuid.uuid4()
    tag_id = uuid.uuid4()

    db = _mock_db(
        [
            _scalar_result([tag_id]),
            _scalar_result([note_id]),
            MagicMock(all=MagicMock(return_value=[])),
        ]
    )

    updated, applied = await bulk_tags_service.bulk_apply_tags(
        db,
        project_id=PROJECT_ID,
        item_type="notes",
        item_ids=[note_id, note_id],
        action="add",
        tag_ids=[tag_id, tag_id],
    )
    assert updated == [note_id]
    assert applied == [tag_id]
    assert db.add.call_count == 1


@pytest.mark.asyncio
async def test_bulk_apply_missing_item_raises() -> None:
    note_id, tag_id = uuid.uuid4(), uuid.uuid4()
    db = _mock_db(
        [
            _scalar_result([tag_id]),
            _scalar_result([]),  # note not found in project
        ]
    )

    with pytest.raises(bulk_tags_service.BulkTagsItemNotFoundError):
        await bulk_tags_service.bulk_apply_tags(
            db,
            project_id=PROJECT_ID,
            item_type="notes",
            item_ids=[note_id],
            action="add",
            tag_ids=[tag_id],
        )
    db.add.assert_not_called()
    db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_bulk_apply_missing_tag_raises() -> None:
    note_id, tag_id = uuid.uuid4(), uuid.uuid4()
    db = _mock_db([_scalar_result([])])  # tag not found in project

    with pytest.raises(bulk_tags_service.BulkTagsTagNotFoundError):
        await bulk_tags_service.bulk_apply_tags(
            db,
            project_id=PROJECT_ID,
            item_type="links",
            item_ids=[note_id],
            action="remove",
            tag_ids=[tag_id],
        )


@pytest.mark.asyncio
async def test_bulk_apply_remove_runs_delete_and_flush() -> None:
    link_ids = [uuid.uuid4()]
    tag_ids = [uuid.uuid4()]
    db = _mock_db(
        [
            _scalar_result(tag_ids),   # tag existence check
            _scalar_result(link_ids),  # link existence check
            MagicMock(),               # delete statement execution
        ]
    )

    updated, applied = await bulk_tags_service.bulk_apply_tags(
        db,
        project_id=PROJECT_ID,
        item_type="links",
        item_ids=link_ids,
        action="remove",
        tag_ids=tag_ids,
    )
    assert updated == link_ids
    assert applied == tag_ids
    assert db.execute.await_count == 3
    db.flush.assert_awaited_once()
    db.add.assert_not_called()
