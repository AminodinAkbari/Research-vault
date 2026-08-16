from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.schemas.roadmap import RoadmapStep
from app.services import roadmap as roadmap_service
from tests.fake_redis import FakeAsyncRedis

VALID_ROADMAP_JSON = json.dumps(
    [
        {"step": "What is Linux?", "keywords": ["linux basics", "linux kernel"]},
        {"step": "Choosing a distro", "keywords": ["ubuntu vs fedora", "beginner linux distro"]},
    ]
)


# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_normalize_subject_collapses_case_and_whitespace() -> None:
    assert roadmap_service._normalize_subject("  Linux   Kernel  ") == "linux kernel"


def test_cache_key_is_stable_across_case_and_whitespace() -> None:
    assert roadmap_service._cache_key("Linux") == roadmap_service._cache_key(" linux ")


def test_extract_json_array_strips_markdown_fence() -> None:
    wrapped = f"Here you go:\n```json\n{VALID_ROADMAP_JSON}\n```"
    assert roadmap_service._extract_json_array(wrapped) == VALID_ROADMAP_JSON


def test_extract_json_array_strips_surrounding_prose() -> None:
    wrapped = f"Sure! {VALID_ROADMAP_JSON} Hope that helps."
    assert roadmap_service._extract_json_array(wrapped) == VALID_ROADMAP_JSON


def test_parse_roadmap_valid_json() -> None:
    steps = roadmap_service._parse_roadmap(VALID_ROADMAP_JSON)
    assert len(steps) == 2
    assert steps[0].step == "What is Linux?"
    assert steps[0].keywords == ["linux basics", "linux kernel"]


def test_parse_roadmap_invalid_json_raises() -> None:
    with pytest.raises(roadmap_service.RoadmapParsingError):
        roadmap_service._parse_roadmap("not json at all")


def test_parse_roadmap_wrong_shape_raises() -> None:
    with pytest.raises(roadmap_service.RoadmapParsingError):
        roadmap_service._parse_roadmap(json.dumps({"not": "a list"}))


def test_parse_roadmap_empty_array_raises() -> None:
    with pytest.raises(roadmap_service.RoadmapParsingError):
        roadmap_service._parse_roadmap(json.dumps([]))


def test_parse_roadmap_missing_required_field_raises() -> None:
    with pytest.raises(roadmap_service.RoadmapParsingError):
        roadmap_service._parse_roadmap(json.dumps([{"keywords": ["x"]}]))


def test_parse_roadmap_missing_keywords_defaults_to_empty_list() -> None:
    steps = roadmap_service._parse_roadmap(json.dumps([{"step": "Only a step"}]))
    assert steps[0].keywords == []


# ---------------------------------------------------------------------------
# generate_roadmap (retry behavior)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_roadmap_succeeds_on_first_try() -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.return_value = VALID_ROADMAP_JSON
        steps = await roadmap_service.generate_roadmap("linux")

    assert len(steps) == 2
    mock_call_ai.assert_called_once()


@pytest.mark.asyncio
async def test_generate_roadmap_retries_once_on_invalid_json() -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.side_effect = ["not valid json", VALID_ROADMAP_JSON]
        steps = await roadmap_service.generate_roadmap("linux")

    assert len(steps) == 2
    assert mock_call_ai.call_count == 2


@pytest.mark.asyncio
async def test_generate_roadmap_raises_after_exhausting_retry() -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.side_effect = ["still not json", "still not json either"]
        with pytest.raises(roadmap_service.RoadmapParsingError):
            await roadmap_service.generate_roadmap("linux")

    assert mock_call_ai.call_count == 2


@pytest.mark.asyncio
async def test_generate_roadmap_does_not_retry_on_generation_error() -> None:
    with patch("app.services.roadmap._call_ai", new_callable=AsyncMock) as mock_call_ai:
        mock_call_ai.side_effect = roadmap_service.RoadmapGenerationError("down")
        with pytest.raises(roadmap_service.RoadmapGenerationError):
            await roadmap_service.generate_roadmap("linux")

    mock_call_ai.assert_called_once()


# ---------------------------------------------------------------------------
# _call_ai
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_ai_raises_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(roadmap_service.settings, "AI_API_KEY", "")
    with pytest.raises(roadmap_service.RoadmapGenerationError):
        await roadmap_service._call_ai("linux")


@pytest.mark.asyncio
async def test_call_ai_raises_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr(roadmap_service.settings, "AI_API_KEY", "test-key")

    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            request = httpx.Request("POST", "https://example.com")
            response = httpx.Response(502, request=request)
            raise httpx.HTTPStatusError("boom", request=request, response=response)

    with patch("app.services.roadmap.httpx.AsyncClient", return_value=_FailingClient()):
        with pytest.raises(roadmap_service.RoadmapGenerationError):
            await roadmap_service._call_ai("linux")


@pytest.mark.asyncio
async def test_call_ai_raises_on_connection_error(monkeypatch) -> None:
    monkeypatch.setattr(roadmap_service.settings, "AI_API_KEY", "test-key")

    class _UnreachableClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    with patch("app.services.roadmap.httpx.AsyncClient", return_value=_UnreachableClient()):
        with pytest.raises(roadmap_service.RoadmapGenerationError):
            await roadmap_service._call_ai("linux")


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_round_trip() -> None:
    fake_redis = FakeAsyncRedis()
    with patch("app.services.roadmap.redis_client", fake_redis):
        assert await roadmap_service.get_cached_roadmap("linux") is None

        steps = [RoadmapStep(step="A", keywords=["a", "b"])]
        await roadmap_service.cache_roadmap("Linux", steps)

        cached = await roadmap_service.get_cached_roadmap("  linux  ")
        assert cached is not None
        assert cached[0].step == "A"


@pytest.mark.asyncio
async def test_get_or_generate_roadmap_uses_cache_when_present() -> None:
    fake_redis = FakeAsyncRedis()
    with patch("app.services.roadmap.redis_client", fake_redis), patch(
        "app.services.roadmap.generate_roadmap", new_callable=AsyncMock
    ) as mock_generate:
        await roadmap_service.cache_roadmap(
            "linux", [RoadmapStep(step="Cached step", keywords=["x"])]
        )

        steps = await roadmap_service.get_or_generate_roadmap("linux")

    assert steps[0].step == "Cached step"
    mock_generate.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_generate_roadmap_generates_and_caches_on_miss() -> None:
    fake_redis = FakeAsyncRedis()
    with patch("app.services.roadmap.redis_client", fake_redis), patch(
        "app.services.roadmap.generate_roadmap", new_callable=AsyncMock
    ) as mock_generate:
        mock_generate.return_value = [RoadmapStep(step="Fresh step", keywords=["y"])]

        steps = await roadmap_service.get_or_generate_roadmap("linux")
        assert steps[0].step == "Fresh step"
        mock_generate.assert_called_once()

        steps_again = await roadmap_service.get_or_generate_roadmap("linux")
        assert steps_again[0].step == "Fresh step"
        mock_generate.assert_called_once()  # second call was served from cache