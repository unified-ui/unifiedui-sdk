"""List service for SharePoint lists (CRUD)."""

from __future__ import annotations

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.models import (
    CreateListItem,
    ListItemsQuery,
    UpdateListItem,
)


class ListService:
    """SharePoint list operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the list service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.LISTS_READ)
    def list(
        self,
        site_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """List all lists on a site."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        data = self._http.request(
            "GET", f"/sites/{site_id}/lists", params=params
        )
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.LISTS_READ)
    def get(
        self,
        site_id: str,
        list_id: str,
        select_fields: list[str] | None = None,
    ) -> dict:
        """Get a list by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET", f"/sites/{site_id}/lists/{list_id}", params=params
        )

    @requires_capability(SharePointCapability.LISTS_READ)
    def get_columns(
        self,
        site_id: str,
        list_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """Get column definitions for a list."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/lists/{list_id}/columns",
            params=params,
        )
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.LISTS_READ)
    def get_items(
        self,
        site_id: str,
        list_id: str,
        query: ListItemsQuery | None = None,
    ) -> PagedResult:
        """Get one page of items from a list."""
        current = query or ListItemsQuery()

        params: dict = {"$top": current.top}
        if current.skip:
            params["$skip"] = current.skip
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)
        if current.filter:
            params["$filter"] = current.filter
        if current.orderby:
            params["$orderby"] = current.orderby
        if current.expand:
            params["$expand"] = current.expand

        data = self._http.request(
            "GET", f"/sites/{site_id}/lists/{list_id}/items", params=params
        )

        return build_paged_result(data, current.top, current.skip)

    @requires_capability(SharePointCapability.LISTS_READ)
    def get_items_all(
        self,
        site_id: str,
        list_id: str,
        query: ListItemsQuery | None = None,
    ) -> list[dict]:
        """Get all items from a list (auto-follows pagination)."""
        current = query or ListItemsQuery()

        params: dict = {"$top": current.top}
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)
        if current.filter:
            params["$filter"] = current.filter
        if current.orderby:
            params["$orderby"] = current.orderby
        if current.expand:
            params["$expand"] = current.expand

        data = self._http.request(
            "GET", f"/sites/{site_id}/lists/{list_id}/items", params=params
        )

        items = data.get("value", [])
        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items

    @requires_capability(SharePointCapability.LISTS_READ)
    def get_item(
        self,
        site_id: str,
        list_id: str,
        item_id: str,
        expand: str | None = None,
    ) -> dict:
        """Get a single list item by ID."""
        params = None
        if expand:
            params = {"$expand": expand}

        return self._http.request(
            "GET",
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}",
            params=params,
        )

    @requires_capability(SharePointCapability.LISTS_WRITE)
    def create_item(
        self,
        site_id: str,
        list_id: str,
        item: CreateListItem,
    ) -> dict:
        """Create a new list item."""
        return self._http.request(
            "POST",
            f"/sites/{site_id}/lists/{list_id}/items",
            json_body={"fields": item.fields},
        )

    @requires_capability(SharePointCapability.LISTS_WRITE)
    def update_item(
        self,
        site_id: str,
        list_id: str,
        item_id: str,
        item: UpdateListItem,
    ) -> dict:
        """Update an existing list item fields."""
        return self._http.request(
            "PATCH",
            f"/sites/{site_id}/lists/{list_id}/items/{item_id}/fields",
            json_body=item.fields,
        )

    @requires_capability(SharePointCapability.LISTS_WRITE)
    def delete_item(
        self,
        site_id: str,
        list_id: str,
        item_id: str,
    ) -> None:
        """Delete a list item."""
        self._http.request(
            "DELETE", f"/sites/{site_id}/lists/{list_id}/items/{item_id}"
        )

    @requires_capability(SharePointCapability.LISTS_WRITE)
    def batch_create(
        self,
        site_id: str,
        list_id: str,
        items: list[CreateListItem],
    ) -> list[dict]:
        """Create multiple list items sequentially."""
        return [self.create_item(site_id, list_id, item) for item in items]


__all__ = ["ListService"]
