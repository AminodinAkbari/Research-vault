from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.requests import Request

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