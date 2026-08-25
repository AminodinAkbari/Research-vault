from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError
from starlette.requests import Request
from starlette.responses import Response

from app.core import rate_limiter
from tests.fake_redis import FakeAsyncRedis


@pytest.mark.asyncio
async def test_check_rate_limit_allows_up_to_max_requests() -> None:
    fake_redis = FakeAsyncRedis()
    with patch("app.core.rate_limiter.redis_client", fake_redis):
        first = await rate_limiter.check_rate_limit("test-key", max_requests=2, window_seconds=60)
        second = await rate_limiter.check_rate_limit("test-key", max_requests=2, window_seconds=60)
        third = await rate_limiter.check_rate_limit("test-key", max_requests=2, window_seconds=60)

    assert first.allowed is True
    assert first.remaining == 1
    assert second.allowed is True
    assert second.remaining == 0
    assert third.allowed is False
    assert third.remaining == 0


@pytest.mark.asyncio
async def test_check_rate_limit_uses_separate_buckets_per_key() -> None:
    fake_redis = FakeAsyncRedis()
    with patch("app.core.rate_limiter.redis_client", fake_redis):
        result_a = await rate_limiter.check_rate_limit("key-a", max_requests=1, window_seconds=60)
        result_b = await rate_limiter.check_rate_limit("key-b", max_requests=1, window_seconds=60)

    assert result_a.allowed is True
    assert result_b.allowed is True


def _make_request(client_host: str | None = "1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/roadmap",
        "headers": [],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_client_identifier_uses_user_id_when_authenticated() -> None:
    class _FakeUser:
        id = "user-123"

    request = _make_request()
    identifier = rate_limiter._client_identifier(request, _FakeUser())
    assert identifier == "user:user-123"


def test_client_identifier_falls_back_to_ip_when_anonymous() -> None:
    request = _make_request(client_host="9.8.7.6")
    identifier = rate_limiter._client_identifier(request, None)
    assert identifier == "ip:9.8.7.6"


def test_client_identifier_handles_missing_client() -> None:
    request = _make_request(client_host=None)
    identifier = rate_limiter._client_identifier(request, None)
    assert identifier == "ip:unknown"


class _FakeUser:
    id = "user-abc"


# ---------------------------------------------------------------------------
# Dependency-factory behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dependency_sets_headers_on_allowed_request() -> None:
    dependency = rate_limiter.create_rate_limit_dependency("dep", max_requests=3, window_seconds=60)
    request = _make_request()
    response = Response()

    with patch("app.core.rate_limiter.redis_client", FakeAsyncRedis()):
        await dependency(request, response, _FakeUser())

    assert response.headers["X-RateLimit-Limit"] == "3"
    assert response.headers["X-RateLimit-Remaining"] == "2"


@pytest.mark.asyncio
async def test_dependency_rejects_after_limit_with_retry_after() -> None:
    dependency = rate_limiter.create_rate_limit_dependency("dep", max_requests=1, window_seconds=60)
    request = _make_request()
    first, second = Response(), Response()

    with patch("app.core.rate_limiter.redis_client", FakeAsyncRedis()):
        await dependency(request, first, _FakeUser())
        with pytest.raises(HTTPException) as exc_info:
            await dependency(request, second, _FakeUser())

    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers


@pytest.mark.asyncio
async def test_dependency_limits_per_user_not_ip() -> None:
    """Two different users behind the same IP get independent buckets."""
    dependency = rate_limiter.create_rate_limit_dependency("dep", max_requests=1, window_seconds=60)
    request = _make_request(client_host="5.6.7.8")

    class _OtherUser:
        id = "user-other"

    user_a_response, other_user_response = Response(), Response()
    with patch("app.core.rate_limiter.redis_client", FakeAsyncRedis()):
        await dependency(request, user_a_response, _FakeUser())
        # Same IP, different user: still allowed.
        await dependency(request, other_user_response, _OtherUser())
        # Same user again: rejected.
        with pytest.raises(HTTPException):
            await dependency(request, Response(), _FakeUser())


@pytest.mark.asyncio
async def test_dependency_falls_back_to_ip_for_anonymous_callers() -> None:
    dependency = rate_limiter.create_rate_limit_dependency("dep", max_requests=1, window_seconds=60)
    request = _make_request(client_host="9.9.9.9")

    with patch("app.core.rate_limiter.redis_client", FakeAsyncRedis()):
        await dependency(request, Response(), None)
        # Anonymous caller from the same IP: rejected.
        with pytest.raises(HTTPException):
            await dependency(request, Response(), None)

# ---------------------------------------------------------------------------
# Redis-unavailable fallback behaviour
# ---------------------------------------------------------------------------


class _BrokenRedis:
    async def incr(self, key: str) -> int:
        raise RedisError("connection refused")

    async def expire(self, key: str, seconds: int) -> bool:
        raise RedisError("connection refused")

    async def ttl(self, key: str) -> int:
        raise RedisError("connection refused")


@pytest.mark.asyncio
async def test_check_rate_limit_fails_open_when_configured() -> None:
    with patch("app.core.rate_limiter.redis_client", _BrokenRedis()), \
         patch("app.core.rate_limiter.settings.RATE_LIMITER_FAIL_OPEN", True):
        result = await rate_limiter.check_rate_limit(
            "some-key", max_requests=5, window_seconds=60
        )

    assert result.allowed is True
    assert result.remaining == -1
    assert result.retry_after_seconds == 60


@pytest.mark.asyncio
async def test_check_rate_limit_fails_closed_when_configured() -> None:
    with patch("app.core.rate_limiter.redis_client", _BrokenRedis()), \
         patch("app.core.rate_limiter.settings.RATE_LIMITER_FAIL_OPEN", False):
        with pytest.raises(HTTPException) as exc_info:
            await rate_limiter.check_rate_limit(
                "some-key", max_requests=5, window_seconds=60
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Rate limiter unavailable"


@pytest.mark.asyncio
async def test_dependency_reports_unknown_remaining_when_failing_open() -> None:
    dependency = rate_limiter.create_rate_limit_dependency("dep", max_requests=5, window_seconds=60)
    response = Response()

    with patch("app.core.rate_limiter.redis_client", _BrokenRedis()), \
         patch("app.core.rate_limiter.settings.RATE_LIMITER_FAIL_OPEN", True):
        await dependency(_make_request(), response, None)

    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "unknown"