"""Site service for SharePoint API operations."""

from typing import Any

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.formatters import parse_site_url
from unifiedui_sdk.tools.m365.sharepoint.models import SiteSearchQuery


class SiteService:
    """SharePoint site operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the site service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.SITES_READ)
    def get_root(
        self,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get the organisation root site."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request("GET", "/sites/root", params=params)

    @requires_capability(SharePointCapability.SITES_READ)
    def get(
        self,
        site_id: str,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a site by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request("GET", f"/sites/{site_id}", params=params)

    @requires_capability(SharePointCapability.SITES_READ)
    def get_by_url(
        self,
        site_url: str,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a site by its full URL."""
        host, path = parse_site_url(site_url)
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request("GET", f"/sites/{host}:/{path}", params=params)

    @requires_capability(SharePointCapability.SITES_READ)
    def list_subsites(
        self,
        site_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """List sub-sites of a site."""
        params: dict[str, Any] = {}
        if select_fields:
            params["$select"] = ",".join(select_fields)

        data = self._http.request("GET", f"/sites/{site_id}/sites", params=params or None)
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.SITES_READ)
    def search(
        self,
        query: SiteSearchQuery | None = None,
    ) -> PagedResult:
        """Search for sites by keyword."""
        current = query or SiteSearchQuery()

        params: dict[str, Any] = {"$top": current.top}
        if current.skip:
            params["$skip"] = current.skip
        if current.keyword:
            params["search"] = current.keyword
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)

        data = self._http.request("GET", "/sites", params=params)
        return build_paged_result(data, current.top, current.skip)

    @requires_capability(SharePointCapability.SITES_READ)
    def search_all(
        self,
        query: SiteSearchQuery | None = None,
    ) -> list[dict[str, Any]]:
        """Search for sites, auto-following pagination."""
        current = query or SiteSearchQuery()

        params: dict[str, Any] = {"$top": current.top}
        if current.keyword:
            params["search"] = current.keyword
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)

        data = self._http.request("GET", "/sites", params=params)

        items: list[dict[str, Any]] = data.get("value", [])
        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items


__all__ = ["SiteService"]
