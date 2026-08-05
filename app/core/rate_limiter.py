from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, Response, status

from app.core.config import settings
from app.core.dependencies import get_optional_current_user
from app.core.redis import redis_client
from app.models.user import User


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
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
    """
    window = int(time.time() // window_seconds)
    redis_key = f"ratelimit:{key}:{window}"

    current = await redis_client.incr(redis_key)
    if current == 1:
        await redis_client.expire(redis_key, window_seconds)

    ttl = await redis_client.ttl(redis_key)
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


async def check_roadmap_rate_limit(
    request: Request,
    response: Response,
    current_user: User | None = Depends(get_optional_current_user),
) -> None:
    """FastAPI dependency guarding POST /api/v1/roadmap.

    Limits requests per authenticated user, or per client IP for anonymous
    callers, using a fixed window sized by the ROADMAP_RATE_LIMIT_* settings.
    Always sets X-RateLimit-* response headers — including on a successful
    request — so callers can see their remaining quota before they hit it.
    """
    identifier = _client_identifier(request, current_user)
    result = await check_rate_limit(
        f"roadmap:{identifier}",
        max_requests=settings.ROADMAP_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=settings.ROADMAP_RATE_LIMIT_WINDOW_SECONDS,
    )

    response.headers["X-RateLimit-Limit"] = str(settings.ROADMAP_RATE_LIMIT_MAX_REQUESTS)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many roadmap requests. Please try again later.",
            headers={
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(settings.ROADMAP_RATE_LIMIT_MAX_REQUESTS),
                "X-RateLimit-Remaining": "0",
            },
        )