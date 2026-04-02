"""Unit tests for Moonshot API client timeout handling."""

from __future__ import annotations

import httpx
import pytest
from shared.config import ClientSettings
from shared.moonshot import MoonshotAPIError, MoonshotClient


def test_moonshot_client_converts_timeout_exception() -> None:
    """Verify that httpx.TimeoutException is converted to MoonshotAPIError."""
    
    class FailingHttpClient:
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ReadTimeout("The read operation timed out")
    
    client = MoonshotClient(
        settings=ClientSettings(
            moonshot_api_key="test-key",
            moonshot_model="test-model",
        ),
        http_client=FailingHttpClient(),  # type: ignore[arg-type]
    )
    
    with pytest.raises(MoonshotAPIError, match="Moonshot API request timed out"):
        client.chat_completion(
            system_prompt="test",
            user_prompt="test",
            tools=[],
        )


def test_moonshot_client_converts_network_error() -> None:
    """Verify that httpx.NetworkError is converted to MoonshotAPIError."""
    
    class FailingHttpClient:
        def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("Connection failed")
    
    client = MoonshotClient(
        settings=ClientSettings(
            moonshot_api_key="test-key",
            moonshot_model="test-model",
        ),
        http_client=FailingHttpClient(),  # type: ignore[arg-type]
    )
    
    with pytest.raises(MoonshotAPIError, match="Moonshot API network error"):
        client.chat_completion(
            system_prompt="test",
            user_prompt="test",
            tools=[],
        )
