"""SharePoint-specific exception aliases."""

from unifiedui_sdk.tools.m365.core.exceptions import (
    M365APIError,
    M365AuthError,
    M365CapabilityError,
    M365ClientError,
)

SharePointClientError = M365ClientError
SharePointAuthError = M365AuthError
SharePointCapabilityError = M365CapabilityError
SharePointAPIError = M365APIError


__all__ = [
    "SharePointAPIError",
    "SharePointAuthError",
    "SharePointCapabilityError",
    "SharePointClientError",
]
