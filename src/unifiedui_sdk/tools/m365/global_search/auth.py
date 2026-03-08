"""Global search authentication provider."""

from unifiedui_sdk.tools.m365.core.auth import GraphAuthProvider


class GraphSearchAuthProvider(GraphAuthProvider):
    """Global search auth provider based on shared Graph auth."""


__all__ = ["GraphSearchAuthProvider"]
