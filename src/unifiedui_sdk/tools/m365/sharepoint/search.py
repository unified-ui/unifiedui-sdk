"""SharePoint-filtered search service using M365 Search API."""

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.models import SearchQuery

_DEFAULT_ENTITY_TYPES = ["driveItem", "listItem", "list", "site"]


class SearchService:
    """Microsoft 365 Search filtered to SharePoint."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the search service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.SEARCH)
    def query(self, query: SearchQuery | None = None) -> PagedResult:
        """Execute SharePoint-scoped search query."""
        current = query or SearchQuery()
        entity_types = current.entity_types or _DEFAULT_ENTITY_TYPES

        request_body: dict = {
            "entityTypes": entity_types,
            "query": {"queryString": current.query},
            "from": current.skip,
            "size": current.top,
        }

        if current.select_fields:
            request_body["fields"] = current.select_fields
        if current.sort_by:
            request_body["sortProperties"] = [
                {"name": current.sort_by, "isDescending": True}
            ]
        if current.region:
            request_body["region"] = current.region

        data = self._http.request(
            "POST", "/search/query", json_body={"requests": [request_body]}
        )

        responses = data.get("value", [])
        if not responses:
            return PagedResult(
                value=[],
                top=current.top,
                skip=current.skip,
                has_more=False,
                total_count=0,
            )

        containers = responses[0].get("hitsContainers", [])
        total = containers[0].get("total", 0) if containers else 0
        more = (
            containers[0].get("moreResultsAvailable", False)
            if containers
            else False
        )
        return PagedResult(
            value=containers,
            top=current.top,
            skip=current.skip,
            has_more=more,
            total_count=total,
        )


__all__ = ["SearchService"]
