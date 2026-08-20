from __future__ import annotations

import json
import re

from app.core.config import settings
from app.core.redis import redis_client
from app.schemas.roadmap import RoadmapStep
from app.services.ai import (
    AIError,
    AIResponseFormatError,
    call_ai,
    extract_json_array,
    parse_json_array,
)

# Forces the model to return nothing but a bare JSON array — no prose, no
# markdown fences, no wrapping object — so the response can be parsed
# directly. _extract_json_array() below is a best-effort fallback in case
# the model doesn't fully comply despite this instruction.
_SYSTEM_PROMPT = (
    "You are a research roadmap generator. Given a subject, respond with "
    "ONLY a JSON array (no prose, no markdown code fences, no explanation) "
    'where each element is an object with exactly two keys: "step" (a '
    'short, human-readable title for that step, e.g. "What is Linux?") and '
    '"keywords" (a JSON array of 2-5 short, search-engine-friendly search '
    'terms for that step, e.g. ["linux basics", "linux kernel"]). Return '
    "between 4 and 8 steps, ordered from foundational to advanced. Do not "
    "wrap the array in an object. Do not include any text besides the JSON "
    "array itself."
)

# One retry on top of the initial attempt, specifically for responses that
# fail to parse — matches "if the AI returns invalid JSON, retry once".
# Network/upstream failures (RoadmapGenerationError) are NOT retried here.
_MAX_PARSE_RETRIES = 1


class RoadmapGenerationError(Exception):
    """Raised when the upstream AI service is unreachable, errors out, or
    returns a response we can't even extract text from. Maps to a 502.
    """


class RoadmapParsingError(Exception):
    """Raised when the AI responded, but its content isn't a valid roadmap
    (bad JSON, wrong shape, missing required fields). Maps to a 422.
    """


def _normalize_subject(subject: str) -> str:
    return re.sub(r"\s+", " ", subject).strip().lower()


def _cache_key(subject: str) -> str:
    return f"roadmap:cache:{_normalize_subject(subject)}"


async def get_cached_roadmap(subject: str) -> list[RoadmapStep] | None:
    raw = await redis_client.get(_cache_key(subject))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        return [RoadmapStep.model_validate(item) for item in data]
    except (json.JSONDecodeError, ValueError, TypeError):
        # A corrupted/stale cache entry shouldn't break the request — treat
        # it as a miss and let a fresh roadmap be generated.
        return None


async def cache_roadmap(subject: str, steps: list[RoadmapStep]) -> None:
    payload = json.dumps([step.model_dump() for step in steps])
    await redis_client.set(_cache_key(subject), payload, ex=settings.ROADMAP_CACHE_TTL_SECONDS)


def _extract_json_array(text: str) -> str:
    """Thin alias for the shared helper in app.services.ai, kept so the
    roadmap module reads self-contained. Parsing lives in one place.
    """
    return extract_json_array(text)


def _parse_roadmap(raw_text: str) -> list[RoadmapStep]:
    try:
        data = parse_json_array(raw_text)
    except AIResponseFormatError as exc:
        raise RoadmapParsingError(str(exc)) from exc

    if not data:
        raise RoadmapParsingError("The AI response was not a non-empty JSON array.")

    try:
        return [RoadmapStep.model_validate(item) for item in data]
    except Exception as exc:  # pydantic ValidationError, TypeError, etc.
        raise RoadmapParsingError(
            "The AI response did not match the expected roadmap format."
        ) from exc


async def generate_roadmap(subject: str) -> list[RoadmapStep]:
    """Call the AI service and parse its response into a roadmap.

    Retries the AI call exactly once if the response can't be parsed into a
    valid roadmap. Does NOT retry on RoadmapGenerationError (network/upstream
    failures) — those propagate immediately.
    """
    last_error: RoadmapParsingError | None = None
    prompt = f"Subject: {subject}"

    for _ in range(_MAX_PARSE_RETRIES + 1):
        try:
            raw_text = await call_ai(prompt, system_prompt=_SYSTEM_PROMPT, temperature=0.3)
        except AIError as exc:
            raise RoadmapGenerationError(str(exc)) from exc
        try:
            return _parse_roadmap(raw_text)
        except RoadmapParsingError as exc:
            last_error = exc
            continue

    assert last_error is not None
    raise last_error


async def get_or_generate_roadmap(subject: str) -> list[RoadmapStep]:
    """Cache-first entry point used by the API route: return a cached
    roadmap for this subject if one exists, otherwise generate one via the
    AI service and cache it for next time.
    """
    cached = await get_cached_roadmap(subject)
    if cached is not None:
        return cached

    steps = await generate_roadmap(subject)
    await cache_roadmap(subject, steps)
    return steps