"""Outlook-specific exception aliases."""

from unifiedui_sdk.tools.m365.core.exceptions import (
    M365APIError,
    M365AuthError,
    M365CapabilityError,
    M365ClientError,
)

OutlookClientError = M365ClientError
OutlookAuthError = M365AuthError
OutlookCapabilityError = M365CapabilityError
OutlookAPIError = M365APIError


__all__ = [
    "OutlookAPIError",
    "OutlookAuthError",
    "OutlookCapabilityError",
    "OutlookClientError",
]
