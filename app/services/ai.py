# filename: app/services/ai.py
from __future__ import annotations

from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import HfHubHTTPError

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