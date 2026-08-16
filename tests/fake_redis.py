from __future__ import annotations

import time
from typing import Optional


class FakeAsyncRedis:
    """A minimal in-memory stand-in for redis.asyncio.Redis, covering just
    the handful of commands used by app/services/roadmap.py and
    app/core/rate_limiter.py (get, set, incr, expire, ttl). Lets tests
    exercise real caching/rate-limiting logic without a live Redis server.
    """

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._expires_at: dict[str, float] = {}

    def _is_expired(self, key: str) -> bool:
        expires_at = self._expires_at.get(key)
        return expires_at is not None and time.time() >= expires_at

    def _purge_if_expired(self, key: str) -> None:
        if self._is_expired(key):
            self._values.pop(key, None)
            self._expires_at.pop(key, None)

    async def get(self, key: str) -> Optional[str]:
        self._purge_if_expired(key)
        return self._values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._values[key] = value
        if ex is not None:
            self._expires_at[key] = time.time() + ex
        else:
            self._expires_at.pop(key, None)
        return True

    async def incr(self, key: str) -> int:
        self._purge_if_expired(key)
        current = int(self._values.get(key, "0"))
        current += 1
        self._values[key] = str(current)
        return current

    async def expire(self, key: str, seconds: int) -> bool:
        if key in self._values:
            self._expires_at[key] = time.time() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        self._purge_if_expired(key)
        if key not in self._values:
            return -2
        expires_at = self._expires_at.get(key)
        if expires_at is None:
            return -1
        return max(0, int(expires_at - time.time()))