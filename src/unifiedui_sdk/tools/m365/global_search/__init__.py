"""Microsoft 365 Global Search client package."""

from unifiedui_sdk.tools.m365.global_search.auth import GraphSearchAuthProvider
from unifiedui_sdk.tools.m365.global_search.client import GraphSearchClient
from unifiedui_sdk.tools.m365.global_search.exceptions import (
    GraphSearchAPIError,
    GraphSearchAuthError,
    GraphSearchClientError,
)
from unifiedui_sdk.tools.m365.global_search.models import (
    ALL_CONTENT_ENTITIES,
    OUTLOOK_ENTITIES,
    SHAREPOINT_ENTITIES,
    TEAMS_ENTITIES,
    BatchSearchQuery,
    EntityType,
    SearchRequest,
)

__all__ = [
    "ALL_CONTENT_ENTITIES",
    "OUTLOOK_ENTITIES",
    "SHAREPOINT_ENTITIES",
    "TEAMS_ENTITIES",
    "BatchSearchQuery",
    "EntityType",
    "GraphSearchAPIError",
    "GraphSearchAuthError",
    "GraphSearchAuthProvider",
    "GraphSearchClient",
    "GraphSearchClientError",
    "SearchRequest",
]
