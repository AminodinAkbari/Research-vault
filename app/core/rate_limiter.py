from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response, status
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.dependencies import get_optional_current_user
from app.core.redis import redis_client
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int  # -1 means unknown (Redis unavailable)
    retry_after_seconds: int


async def check_rate_limit(
    key: str, *, max_requests: int, window_seconds: int
) -> RateLimitResult:
    """A simple Redis-backed fixed-window rate limiter.

    Requests are bucketed by the current wall-clock time into
    `window_seconds`-wide windows, so a key's count resets cleanly at each
    window boundary rather than needing a sliding-window computation.
    `INCR` on a fresh key returns 1 and we set its TTL right then, so stale
    windows expire out of Redis on their own instead of accumulating.

    Fails open: if Redis is unavailable, requests are allowed and the
    remaining quota is reported as unknown rather than taking the whole
    API down with the cache.
    """
    window = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{key}:{window}"

    try:
        current = await redis_client.incr(redis_key)
        if current == 1:
            await redis_client.expire(redis_key, window_seconds)
        ttl = await redis_client.ttl(redis_key)
    except RedisError:
        logger.warning(
            "Rate limiter unavailable (Redis error); allowing request for key %s", key
        )
        return RateLimitResult(
            allowed=True, remaining=-1, retry_after_seconds=window_seconds
        )

    retry_after = ttl if ttl and ttl > 0 else window_seconds
    remaining = max(0, max_requests - current)

    return RateLimitResult(
        allowed=current <= max_requests,
        remaining=remaining,
        retry_after_seconds=retry_after,
    )


def _client_identifier(request: Request, current_user: User | None) -> str:
    """Prefer a stable per-user key when authenticated; fall back to the
    client's IP address for anonymous callers.
    """
    if current_user is not None:
        return f"user:{current_user.id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _remaining_header(result: RateLimitResult) -> str:
    return str(result.remaining) if result.remaining >= 0 else "unknown"


def create_rate_limit_dependency(
    key_prefix: str,
    max_requests: int,
    window_seconds: int,
) -> Callable[..., Awaitable[None]]:
    """FastAPI dependency enforcing a fixed-window limit.

    Keys are scoped per caller (authenticated user ID when available, client
    IP otherwise) under `key_prefix`. Always sets X-RateLimit-* headers —
    including on successful requests — so callers can see their remaining
    quota before they hit it.
    """

    async def dependency(
        request: Request,
        response: Response,
        current_user: User | None = Depends(get_optional_current_user),
    ) -> None:
        identifier = _client_identifier(request, current_user)
        result = await check_rate_limit(
            f"{key_prefix}:{identifier}",
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = _remaining_header(result)

        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(result.retry_after_seconds),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

    return dependency


# Shared AI budget for all AI-backed endpoints (roadmap, summarise, explain,
# suggest-tags, search-semantic), sized by the AI_RATE_LIMIT_* settings.
ai_rate_limit = create_rate_limit_dependency(
    "ai",
    max_requests=settings.AI_RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.AI_RATE_LIMIT_WINDOW_SECONDS,
)

# Brute-force protection for unauthenticated endpoints. Register/login never
# carry credentials yet, so this is always IP-keyed.
auth_rate_limit = create_rate_limit_dependency(
    "auth",
    max_requests=settings.AUTH_RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
)
