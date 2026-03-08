"""Tests for the main UnifiedUIClient."""

from __future__ import annotations

from unifiedui_sdk.client.client import UnifiedUIClient
from unifiedui_sdk.client.config import ClientConfig
from unifiedui_sdk.client.tracing import TracingService


def _make_client() -> UnifiedUIClient:
    """Create a client with test config."""
    config = ClientConfig(
        base_url="https://api.test.com",
        tenant_id="t-1",
        bearer_token="tok",
    )
    return UnifiedUIClient(config)


class TestUnifiedUIClient:
    """Tests for UnifiedUIClient initialization and properties."""

    def test_exposes_config(self) -> None:
        client = _make_client()
        assert client.config.base_url == "https://api.test.com"
        assert client.config.tenant_id == "t-1"

    def test_provides_tracing_service(self) -> None:
        client = _make_client()
        assert isinstance(client.tracing, TracingService)

    def test_tracing_service_is_stable_reference(self) -> None:
        client = _make_client()
        assert client.tracing is client.tracing
