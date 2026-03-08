"""Client module — HTTP client for the unified-ui agent service API."""

from unifiedui_sdk.client.client import UnifiedUIClient
from unifiedui_sdk.client.config import ClientConfig
from unifiedui_sdk.client.errors import (
    APIError,
    AuthenticationError,
    ClientError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "ClientConfig",
    "ClientError",
    "ConflictError",
    "NotFoundError",
    "UnifiedUIClient",
    "ValidationError",
]
