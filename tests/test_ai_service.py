# filename: tests/test_ai_service.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from huggingface_hub.errors import HfHubHTTPError
import pytest

from app.services.ai import AIError, call_ai


@pytest.mark.asyncio
@patch("app.services.ai.AsyncInferenceClient")
async def test_call_ai_success(mock_client_constructor):
    mock_client = AsyncMock()
    mock_client_constructor.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a concise explanation."
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        mock_settings.AI_BASE_URL = "https://test.com"
        mock_settings.AI_MODEL = "gpt-test"

        result = await call_ai("Please explain this.", "System prompt")
        assert result == "This is a concise explanation."

    # Check that the client was created with the correct parameters
    mock_client_constructor.assert_called_once_with(
        api_key="test_key",
        provider="auto",
    )
    # Check that chat.completions.create was called with the correct parameters
    mock_client.chat.completions.create.assert_called_once()
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-test"
    assert call_args["messages"] == [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Please explain this."},
    ]


@pytest.mark.asyncio
@patch("app.services.ai.AsyncInferenceClient")
async def test_call_ai_omits_system_message_when_not_given(mock_client_constructor):
    mock_client = AsyncMock()
    mock_client_constructor.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "hi"
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        mock_settings.AI_BASE_URL = "https://test.com"
        mock_settings.AI_MODEL = "gpt-test"

        assert await call_ai("just a user prompt") == "hi"

    mock_client.chat.completions.create.assert_called_once()
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["messages"] == [{"role": "user", "content": "just a user prompt"}]
    assert "temperature" not in call_args


@pytest.mark.asyncio
@patch("app.services.ai.AsyncInferenceClient")
async def test_call_ai_network_error(mock_client_constructor):
    mock_client = AsyncMock()
    mock_client_constructor.return_value = mock_client
    mock_client.chat.completions.create.side_effect = Exception("Network unavailable")

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"

        with pytest.raises(AIError):
            await call_ai("test", "test")


@pytest.mark.asyncio
async def test_call_ai_raises_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ai.settings.AI_API_KEY", "test-key")

    async def _create(*args, **kwargs):
        request = httpx.Request("POST", "https://example.com")
        response = httpx.Response(502, request=request)
        raise HfHubHTTPError("boom", response=response)

    with patch("app.services.ai.AsyncInferenceClient") as mock_client_constructor:
        mock_client = AsyncMock()
        mock_client_constructor.return_value = mock_client
        mock_client.chat.completions.create.side_effect = lambda *args, **kwargs: _create(*args, **kwargs)

        with pytest.raises(AIError):
            await call_ai("linux", "system")


@pytest.mark.asyncio
async def test_call_ai_raises_on_connection_error(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ai.settings.AI_API_KEY", "test-key")

    async def _create(*args, **kwargs):
        raise Exception("connection refused")

    with patch("app.services.ai.AsyncInferenceClient") as mock_client_constructor:
        mock_client = AsyncMock()
        mock_client_constructor.return_value = mock_client
        mock_client.chat.completions.create.side_effect = lambda *args, **kwargs: _create(*args, **kwargs)

        with pytest.raises(AIError):
            await call_ai("linux", "system")


@pytest.mark.asyncio
@patch("app.services.ai.AsyncInferenceClient")
async def test_call_ai_raises_on_unexpected_shape(mock_client_constructor):
    mock_client = AsyncMock()
    mock_client_constructor.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = []
    mock_client.chat.completions.create.return_value = mock_response

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        mock_settings.AI_BASE_URL = "https://test.com"
        mock_settings.AI_MODEL = "gpt-test"

        with pytest.raises(AIError):
            await call_ai("test", "test")


@pytest.mark.asyncio
async def test_call_ai_missing_api_key():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = None

        with pytest.raises(AIError) as exc_info:
            await call_ai("test", "test")

        assert "not configured" in str(exc_info.value)