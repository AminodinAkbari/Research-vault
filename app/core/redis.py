from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import settings

# Single shared async Redis client, reused across the app for both roadmap
# response caching (app/services/roadmap.py) and rate limiting
# (app/core/rate_limiter.py). Points at the same Redis instance already used
# as the Celery broker/backend (REDIS_URL) — distinct key prefixes
# ("roadmap:cache:", "ratelimit:") keep the two use cases from colliding.
redis_client: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)