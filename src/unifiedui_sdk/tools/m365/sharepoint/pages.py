"""Page service for SharePoint site pages."""

from __future__ import annotations

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.formatters import (
    extract_webparts_html,
    html_to_plain_text,
)
from unifiedui_sdk.tools.m365.sharepoint.models import PagesQuery


class PageService:
    """SharePoint site page operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the page service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.PAGES_READ)
    def list(
        self,
        site_id: str,
        query: PagesQuery | None = None,
    ) -> PagedResult:
        """List site pages."""
        current = query or PagesQuery()

        params: dict = {"$top": current.top}
        if current.skip:
            params["$skip"] = current.skip
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)
        if current.filter:
            params["$filter"] = current.filter
        if current.orderby:
            params["$orderby"] = current.orderby

        data = self._http.request(
            "GET", f"/sites/{site_id}/pages", params=params
        )
        return build_paged_result(data, current.top, current.skip)

    @requires_capability(SharePointCapability.PAGES_READ)
    def list_all(
        self,
        site_id: str,
        query: PagesQuery | None = None,
    ) -> list[dict]:
        """List all site pages, auto-following pagination."""
        current = query or PagesQuery()

        params: dict = {"$top": current.top}
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)
        if current.filter:
            params["$filter"] = current.filter
        if current.orderby:
            params["$orderby"] = current.orderby

        data = self._http.request(
            "GET", f"/sites/{site_id}/pages", params=params
        )

        items = data.get("value", [])
        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items

    @requires_capability(SharePointCapability.PAGES_READ)
    def get(
        self,
        site_id: str,
        page_id: str,
        select_fields: list[str] | None = None,
    ) -> dict:
        """Get a page by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET", f"/sites/{site_id}/pages/{page_id}", params=params
        )

    @requires_capability(SharePointCapability.PAGES_READ)
    def get_webparts(self, site_id: str, page_id: str) -> list[dict]:
        """Get all web parts of a page."""
        data = self._http.request(
            "GET",
            f"/sites/{site_id}/pages/{page_id}/microsoft.graph.sitePage"
            "/webParts",
        )
        return data.get("value", [])

    @requires_capability(SharePointCapability.PAGES_READ)
    def get_content(self, site_id: str, page_id: str) -> str:
        """Get page content as combined HTML."""
        webparts = self.get_webparts(site_id, page_id)
        return extract_webparts_html(webparts)

    @requires_capability(SharePointCapability.PAGES_READ)
    def get_plain_text(self, site_id: str, page_id: str) -> str:
        """Get page content as plain text."""
        html = self.get_content(site_id, page_id)
        return html_to_plain_text(html)


__all__ = ["PageService"]
