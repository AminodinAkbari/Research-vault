from __future__ import annotations

import json
import logging
import os
import re

import httpx
from huggingface_hub import AsyncInferenceClient
from huggingface_hub.errors import HfHubHTTPError

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIError(Exception):
    """Raised when the AI service is unconfigured, unreachable, or fails."""


class AIResponseFormatError(ValueError):
    """Raised when the AI response is not formatted as expected."""


async def _call_huggingface(messages: list[dict[str, str]], temperature: float | None) -> str:
    """Helper for Hugging Face."""
    # Removed deprecated 'proxies' argument. Reads OS env vars automatically.
    client = AsyncInferenceClient(
        api_key=settings.HF_API_KEY,
        provider="auto",
    )
    kwargs: dict[str, object] = {
        "model": "deepseek-ai/DeepSeek-V3-0324",
        "messages": messages,
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    completion = await client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content.strip()


async def _call_openai_compatible(
    base_url: str, api_key: str, model: str, messages: list[dict[str, str]], temperature: float | None
) -> str:
    """Helper for standard OpenAI-compatible endpoints."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, object] = {"model": model, "messages": messages}
    if temperature is not None:
        payload["temperature"] = temperature

    # connect timeout (5s) ensures blocked endpoints fail quickly without hanging
    timeout = httpx.Timeout(30.0, connect=5.0)

    # Removed 'proxy=' argument. httpx reads OS env vars automatically.
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    body = response.json()
    return body["choices"][0]["message"]["content"].strip()


async def call_ai(
    user_prompt: str,
    system_prompt: str | None = None,
    *,
    temperature: float | None = None,
) -> str:
    """Waterfall routing across available AI providers."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    providers = []

    # 1. OpenRouter (Primary if available)
    if getattr(settings, "OPENROUTER_API_KEY", None):
        providers.append({
            "name": "OpenRouter",
            "func": _call_openai_compatible,
            "kwargs": {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": settings.OPENROUTER_API_KEY,
                "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                "messages": messages,
                "temperature": temperature,
            },
        })

    # 2. Hugging Face (Works directly without a proxy in many regions)
    if getattr(settings, "HF_API_KEY", None):
        providers.append({
            "name": "HuggingFace",
            "func": _call_huggingface,
            "kwargs": {"messages": messages, "temperature": temperature},
        })

    # 3. Groq
    if getattr(settings, "GROQ_API_KEY", None):
        providers.append({
            "name": "Groq",
            "func": _call_openai_compatible,
            "kwargs": {
                "base_url": "https://api.groq.com/openai/v1",
                "api_key": settings.GROQ_API_KEY,
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": temperature,
            },
        })

    if not providers:
        raise AIError("No AI providers are configured. Please set at least one API key in your .env file.")

    last_error = None
    for provider in providers:
        try:
            logger.info(f"Attempting AI request with provider: {provider['name']}...")
            
            result = await provider["func"](**provider["kwargs"])
            
            logger.info(f"AI request successfully fulfilled by provider: {provider['name']}.")
            return result
            
        except Exception as exc:
            err_msg = str(exc).lower()
            # Check if docker-compose injected the HTTP_PROXY. If not, suggest they uncomment it.
            if not os.environ.get("HTTP_PROXY") and ("timeout" in err_msg or "connect" in err_msg):
                logger.warning(
                    f"\n⚠️  [{provider['name']}] Connection blocked or timed out!\n"
                    f"This provider is likely blocking connections due to regional restrictions.\n"
                    f"To bypass this, enable NekoRay/Hiddify with these steps:\n"
                    f"  1. In your proxy client, set 'Listen Address' to 0.0.0.0 or enable 'Allow LAN'.\n"
                    f"  2. Open your Ubuntu firewall: `sudo ufw allow 2080/tcp` (replace 2080 with your proxy port).\n"
                    f"  3. Uncomment the HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, and NO_PROXY lines in your docker-compose.yml.\n"
                    f"  4. Recreate containers: docker compose down && docker compose up -d\n"
                    f"Falling back to the next provider...\n"
                )
            else:
                logger.warning(f"[{provider['name']}] failed: {exc}. Falling back to next provider...")
                
            last_error = exc
            continue

    raise AIError(f"All configured AI providers failed. Last error: {last_error}")


# ---------------------------------------------------------------------------
# Shared response parsing helpers
# ---------------------------------------------------------------------------


def extract_json_array(text: str) -> str:
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
    candidate = extract_json_array(raw_text)
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        print("candidates: " , candidate)
        raise AIResponseFormatError("The AI response was not valid JSON.") from exc

    if not isinstance(data, list):
        raise AIResponseFormatError("The AI response was not a JSON array.")

    return data


def parse_json_string_array(raw_text: str) -> list[str]:
    return [item for item in parse_json_array(raw_text) if isinstance(item, str)]