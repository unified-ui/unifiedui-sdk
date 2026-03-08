"""OneNote service for SharePoint site notebooks."""

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.formatters import html_to_plain_text


class OneNoteService:
    """OneNote operations scoped to a SharePoint site."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the OneNote service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def list_notebooks(
        self,
        site_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """List all notebooks on a site."""
        params: dict = {}
        if select_fields:
            params["$select"] = ",".join(select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/onenote/notebooks",
            params=params or None,
        )
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def get_notebook(
        self,
        site_id: str,
        notebook_id: str,
        select_fields: list[str] | None = None,
    ) -> dict:
        """Get a specific notebook."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET",
            f"/sites/{site_id}/onenote/notebooks/{notebook_id}",
            params=params,
        )

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def list_sections(
        self,
        site_id: str,
        notebook_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """List sections in a notebook."""
        params: dict = {}
        if select_fields:
            params["$select"] = ",".join(select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/onenote/notebooks/{notebook_id}/sections",
            params=params or None,
        )
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def list_pages(
        self,
        site_id: str,
        section_id: str,
        select_fields: list[str] | None = None,
        top: int = 100,
        skip: int = 0,
    ) -> PagedResult:
        """List pages in a section."""
        params: dict = {"$top": top}
        if skip:
            params["$skip"] = skip
        if select_fields:
            params["$select"] = ",".join(select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/onenote/sections/{section_id}/pages",
            params=params,
        )
        return build_paged_result(data, top, skip)

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def list_pages_all(
        self,
        site_id: str,
        section_id: str,
        select_fields: list[str] | None = None,
        top: int = 100,
    ) -> list[dict]:
        """List all pages in a section, auto-following pagination."""
        params: dict = {"$top": top}
        if select_fields:
            params["$select"] = ",".join(select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/onenote/sections/{section_id}/pages",
            params=params,
        )

        items = data.get("value", [])
        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def get_page_content(self, site_id: str, page_id: str) -> str:
        """Get OneNote page content as raw HTML."""
        raw = self._http.request_raw(
            "GET", f"/sites/{site_id}/onenote/pages/{page_id}/content"
        )
        return raw.decode("utf-8", errors="replace")

    @requires_capability(SharePointCapability.ONENOTE_READ)
    def get_page_plain_text(self, site_id: str, page_id: str) -> str:
        """Get OneNote page content as plain text."""
        html = self.get_page_content(site_id, page_id)
        return html_to_plain_text(html)


__all__ = ["OneNoteService"]
