from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.fake_redis import FakeAsyncRedis

VALID_ROADMAP_JSON = json.dumps(
    [
        {"step": "What is Linux?", "keywords": ["linux basics", "linux kernel"]},
        {"step": "Choosing a distro", "keywords": ["ubuntu vs fedora"]},
    ]
)


@pytest.fixture(autouse=True)
def _fake_redis_for_roadmap():
    """Route both the roadmap cache and the rate limiter through an
    in-memory fake Redis for every test in this module, so tests never
    depend on (or pollute) a real Redis instance.
    """
    fake_redis = FakeAsyncRedis()
    with patch("app.services.roadmap.redis_client", fake_redis), patch(
        "app.core.rate_limiter.redis_client", fake_redis
    ):
        yield fake_redis


@pytest.mark.asyncio
async def test_create_roadmap_success(client: AsyncClient) -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON
        response = await client.post("/api/v1/roadmap", json={"subject": "linux"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["roadmap"]) == 2
    assert body["roadmap"][0]["step"] == "What is Linux?"
    assert "linux basics" in body["roadmap"][0]["keywords"]
    mock_call_ai.assert_called_once()


@pytest.mark.asyncio
async def test_create_roadmap_uses_cache_on_second_call(client: AsyncClient) -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON

        first = await client.post("/api/v1/roadmap", json={"subject": "Linux"})
        second = await client.post("/api/v1/roadmap", json={"subject": "  linux  "})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    mock_call_ai.assert_called_once()  # second call was served from cache


@pytest.mark.asyncio
async def test_create_roadmap_blank_subject_rejected(client: AsyncClient) -> None:
    response = await client.post("/api/v1/roadmap", json={"subject": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_roadmap_ai_unavailable_returns_502(client: AsyncClient) -> None:
    from app.services import roadmap as roadmap_service

    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.side_effect = roadmap_service.RoadmapGenerationError(
            "The AI service is unavailable."
        )
        response = await client.post("/api/v1/roadmap", json={"subject": "linux"})

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_roadmap_invalid_ai_response_returns_422(client: AsyncClient) -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = "not json at all, sorry"
        response = await client.post("/api/v1/roadmap", json={"subject": "linux"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_roadmap_sets_rate_limit_headers(client: AsyncClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_MAX_REQUESTS", 5)
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_WINDOW_SECONDS", 60)

    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON
        response = await client.post("/api/v1/roadmap", json={"subject": "networking"})

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"


@pytest.mark.asyncio
async def test_create_roadmap_rate_limit_exceeded_returns_429(
    client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_WINDOW_SECONDS", 60)

    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON

        # Distinct subjects so caching doesn't short-circuit the AI call and
        # mask the rate limiter's own counting.
        first = await client.post("/api/v1/roadmap", json={"subject": "subject one"})
        second = await client.post("/api/v1/roadmap", json={"subject": "subject two"})
        third = await client.post("/api/v1/roadmap", json={"subject": "subject three"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in third.headers


@pytest.mark.asyncio
async def test_create_roadmap_rate_limit_is_per_authenticated_user(
    client: AsyncClient, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(settings, "ROADMAP_RATE_LIMIT_WINDOW_SECONDS", 60)

    _, headers_a = await make_user()
    _, headers_b = await make_user()

    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON

        resp_a = await client.post(
            "/api/v1/roadmap", json={"subject": "topic a"}, headers=headers_a
        )
        resp_a_again = await client.post(
            "/api/v1/roadmap", json={"subject": "topic a again"}, headers=headers_a
        )
        resp_b = await client.post(
            "/api/v1/roadmap", json={"subject": "topic b"}, headers=headers_b
        )

    assert resp_a.status_code == 200
    assert resp_a_again.status_code == 429  # same user, second request in window
    assert resp_b.status_code == 200  # different user, separate bucket