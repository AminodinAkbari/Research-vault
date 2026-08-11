from __future__ import annotations

import httpx

from app.core.config import settings

class AIError(Exception):
    """Raised when the AI service request fails."""
    pass

async def call_ai(prompt: str, system_message: str) -> str:
    """
    Calls an OpenAI-compatible chat completions endpoint.
    """
    if not settings.AI_API_KEY:
        raise AIError("AI_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {settings.AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": settings.AI_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.AI_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except (httpx.RequestError, httpx.HTTPStatusError, KeyError, IndexError) as exc:
        raise AIError(f"Failed to call AI service: {exc}") from exc