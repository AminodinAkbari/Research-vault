# filename: app/services/ai.py
from __future__ import annotations

import json
import re

from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.core.config import settings


class AIError(Exception):
    """Raised when the AI service is unconfigured, unreachable, errors out, or
    returns a response we can't extract text from.
    """


class AIResponseFormatError(ValueError):
    """Raised when the AI responded, but its content isn't in the shape the
    caller asked for (e.g. not a JSON array).

    Distinct from AIError: the service worked, the content didn't.
    """


async def call_ai(
    user_prompt: str,
    system_prompt: str | None = None,
    *,
    temperature: float | None = None,
) -> str:
    """Call an OpenAI-compatible chat-completions endpoint using the Hugging Face
    Inference Client.

    This is the single shared entry point for every AI-backed feature.
    """
    if not settings.AI_API_KEY:
        raise AIError("The AI service is not configured.")

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    # Initialize the async client using the "auto" provider to bypass blocks
    client = AsyncInferenceClient(
        api_key=settings.AI_API_KEY,
        provider="auto",
    )

    kwargs: dict[str, object] = {
        "model": settings.AI_MODEL,
        "messages": messages,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    try:
        completion = await client.chat.completions.create(**kwargs)
        return completion.choices[0].message.content.strip()
    except HfHubHTTPError as exc:
        raise AIError(f"The AI service returned an error: {exc}") from exc
    except Exception as exc:
        # Catches timeouts, connection errors, or malformed data shapes
        raise AIError(f"The AI service is unavailable or failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Shared response parsing
#
# Every JSON-array-returning feature (roadmap, tag suggestion, semantic
# reranking) hits the same two problems: models wrap the array in a markdown
# fence, and they pad it with prose. These helpers live here so that parsing
# logic exists in exactly one place alongside call_ai itself.
# ---------------------------------------------------------------------------


def extract_json_array(text: str) -> str:
    """Best-effort extraction of a JSON array from a model's raw output.

    Handles markdown code fences and stray text around the array. Returns the
    input unchanged when no array-looking substring is found, so the caller's
    json.loads() produces the error.
    """
    text = text.strip()

    fence_match = re.search(r"```(?:json)?\s*(\[.*\])\s*```", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1)

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]

    return text


def parse_json_array(raw_text: str) -> list:
    """Parse a model response that is expected to be a JSON array.

    Raises AIResponseFormatError if the text isn't valid JSON or isn't a list.
    An empty array is valid — "no results" is a legitimate answer for tag
    suggestion and reranking alike.
    """
    candidate = extract_json_array(raw_text)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("The AI response was not valid JSON.") from exc

    if not isinstance(data, list):
        raise AIResponseFormatError("The AI response was not a JSON array.")

    return data


def parse_json_string_array(raw_text: str) -> list[str]:
    """Like parse_json_array, but keeps only the string elements.

    Non-string entries (numbers, nested objects) are dropped rather than
    raising, since a partially well-formed list is still usable.
    """
    return [item for item in parse_json_array(raw_text) if isinstance(item, str)]
