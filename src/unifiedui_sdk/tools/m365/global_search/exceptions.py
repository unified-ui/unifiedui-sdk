"""Global search-specific exception aliases."""

from unifiedui_sdk.tools.m365.core.exceptions import (
    M365APIError,
    M365AuthError,
    M365ClientError,
)

GraphSearchClientError = M365ClientError
GraphSearchAuthError = M365AuthError
GraphSearchAPIError = M365APIError


__all__ = [
    "GraphSearchAPIError",
    "GraphSearchAuthError",
    "GraphSearchClientError",
]
