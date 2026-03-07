"""Unified-UI client — main entry point for the unified-ui agent service API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unifiedui_sdk.client.http import HTTPTransport
from unifiedui_sdk.client.tracing import TracingService

if TYPE_CHECKING:
    from unifiedui_sdk.client.config import ClientConfig


class UnifiedUIClient:
    """Client for the unified-ui agent service API.

    Provides access to service-specific sub-clients (e.g. ``tracing``).
    Designed for extensibility — new services can be added as properties.

    Example::

        from unifiedui_sdk.client import UnifiedUIClient, ClientConfig

        config = ClientConfig(
            base_url="https://agent.unified-ui.com",
            tenant_id="my-tenant",
            api_key="my-api-key",
        )
        client = UnifiedUIClient(config)

        trace_id = client.tracing.create_trace(trace)
    """

    def __init__(self, config: ClientConfig) -> None:
        """Initialize the unified-ui client.

        Args:
            config: Client configuration with connection and auth settings.
        """
        self._config = config
        self._transport = HTTPTransport(config)
        self._tracing = TracingService(self._transport)

    @property
    def config(self) -> ClientConfig:
        """Return the client configuration."""
        return self._config

    @property
    def tracing(self) -> TracingService:
        """Access the tracing service for trace CRUD operations."""
        return self._tracing
