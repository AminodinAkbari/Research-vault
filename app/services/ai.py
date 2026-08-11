from __future__ import annotations

import httpx

from app.core.config import settings


class AIError(Exception):
    """Raised when the AI service is unconfigured, unreachable, errors out, or
    returns a response we can't extract text from.
    """


async def call_ai(
    user_prompt: str,
    system_prompt: str | None = None,
    *,
    temperature: float | None = None,
) -> str:
    """Call an OpenAI-compatible chat-completions endpoint (OpenRouter by
    default) and return the text content of the model's reply.

    This is the single shared entry point for every AI-backed feature.
    """
    if not settings.AI_API_KEY:
        raise AIError("The AI service is not configured.")

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    payload: dict[str, object] = {
        "model": settings.AI_MODEL,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AIError(
            f"The AI service returned an error: {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise AIError("The AI service is unavailable.") from exc

    try:
        body = response.json()
    except ValueError as exc:
        raise AIError("The AI service returned a non-JSON response.") from exc

    try:
        return body["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise AIError("The AI service returned an unexpected response shape.") from exc
