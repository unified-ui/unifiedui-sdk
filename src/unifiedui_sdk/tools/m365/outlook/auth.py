"""Outlook authentication provider."""

from unifiedui_sdk.tools.m365.core.auth import GraphAuthProvider


class OutlookAuthProvider(GraphAuthProvider):
    """Outlook auth provider based on shared Graph auth."""


__all__ = ["OutlookAuthProvider"]
