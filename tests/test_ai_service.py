# filename: tests/test_ai_service.py
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.services.ai import AIError, call_ai


def _client(post):
    """Build a stand-in for httpx.AsyncClient whose .post is `post`."""

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            return await post_fn(*args, **kwargs)

    post_fn = post
    return _Client()


@pytest.mark.asyncio
@patch("app.services.ai.httpx.AsyncClient.post")
async def test_call_ai_success(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "This is a concise explanation."}}]
    }
    mock_post.return_value = mock_response

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        mock_settings.AI_BASE_URL = "https://test.com"
        mock_settings.AI_MODEL = "gpt-test"

        result = await call_ai("Please explain this.", "System prompt")
        assert result == "This is a concise explanation."

    payload = mock_post.call_args.kwargs["json"]
    assert payload["messages"] == [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Please explain this."},
    ]


@pytest.mark.asyncio
@patch("app.services.ai.httpx.AsyncClient.post")
async def test_call_ai_omits_system_message_when_not_given(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"choices": [{"message": {"content": "hi"}}]}
    mock_post.return_value = mock_response

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        mock_settings.AI_BASE_URL = "https://test.com"
        mock_settings.AI_MODEL = "gpt-test"

        assert await call_ai("just a user prompt") == "hi"

    payload = mock_post.call_args.kwargs["json"]
    assert payload["messages"] == [{"role": "user", "content": "just a user prompt"}]
    assert "temperature" not in payload


@pytest.mark.asyncio
@patch("app.services.ai.httpx.AsyncClient.post")
async def test_call_ai_network_error(mock_post):
    mock_post.side_effect = httpx.RequestError("Network unavailable")

    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"

        with pytest.raises(AIError):
            await call_ai("test", "test")


@pytest.mark.asyncio
async def test_call_ai_raises_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ai.settings.AI_API_KEY", "test-key")

    async def _post(*args, **kwargs):
        request = httpx.Request("POST", "https://example.com")
        response = httpx.Response(502, request=request)
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    with patch("app.services.ai.httpx.AsyncClient", return_value=_client(_post)):
        with pytest.raises(AIError):
            await call_ai("linux", "system")


@pytest.mark.asyncio
async def test_call_ai_raises_on_connection_error(monkeypatch) -> None:
    monkeypatch.setattr("app.services.ai.settings.AI_API_KEY", "test-key")

    async def _post(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    with patch("app.services.ai.httpx.AsyncClient", return_value=_client(_post)):
        with pytest.raises(AIError):
            await call_ai("linux", "system")


@pytest.mark.asyncio
@patch("app.services.ai.httpx.AsyncClient.post")
async def test_call_ai_raises_on_unexpected_shape(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"error": "nope"}
    mock_post.return_value = mock_response

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
