# filename: tests/test_ai_service.py
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest
import httpx

from app.services.ai import call_ai, AIError


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


@pytest.mark.asyncio
@patch("app.services.ai.httpx.AsyncClient.post")
async def test_call_ai_network_error(mock_post):
    mock_post.side_effect = httpx.RequestError("Network unavailable")
    
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = "test_key"
        
        with pytest.raises(AIError):
            await call_ai("test", "test")


@pytest.mark.asyncio
async def test_call_ai_missing_api_key():
    with patch("app.services.ai.settings") as mock_settings:
        mock_settings.AI_API_KEY = None
        
        with pytest.raises(AIError) as exc_info:
            await call_ai("test", "test")
            
        assert "AI_API_KEY is not configured" in str(exc_info.value)