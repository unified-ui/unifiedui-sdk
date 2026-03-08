"""Shared core building blocks for M365 Graph clients."""

from unifiedui_sdk.tools.m365.core.auth import GraphAuthProvider, TokenCredential
from unifiedui_sdk.tools.m365.core.exceptions import (
    M365APIError,
    M365AuthError,
    M365CapabilityError,
    M365ClientError,
)
from unifiedui_sdk.tools.m365.core.http import GRAPH_BASE_URL, GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result

__all__ = [
    "GRAPH_BASE_URL",
    "GraphAuthProvider",
    "GraphRequestHandler",
    "M365APIError",
    "M365AuthError",
    "M365CapabilityError",
    "M365ClientError",
    "PagedResult",
    "TokenCredential",
    "build_paged_result",
]
