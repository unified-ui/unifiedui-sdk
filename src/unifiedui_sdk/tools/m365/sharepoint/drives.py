"""Drive service for SharePoint document libraries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from unifiedui_sdk.tools.m365.core.http import GRAPH_BASE_URL, GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.sharepoint.capabilities import (
    SharePointCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.sharepoint.formatters import get_folder_path
from unifiedui_sdk.tools.m365.sharepoint.models import (
    DeltaQuery,
    DriveItemsQuery,
    DriveSearchQuery,
    UploadFile,
)

if TYPE_CHECKING:
    import builtins
    from collections.abc import Generator


class DriveService:
    """SharePoint drives / document-library operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[SharePointCapability],
    ) -> None:
        """Initialize the drive service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._http = http
        self._capabilities = capabilities

    @requires_capability(SharePointCapability.DRIVES_READ)
    def list(
        self,
        site_id: str,
        select_fields: list[str] | None = None,
    ) -> PagedResult:
        """List all drives for a site."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        data = self._http.request("GET", f"/sites/{site_id}/drives", params=params)
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(SharePointCapability.DRIVES_READ)
    def get(
        self,
        site_id: str,
        drive_id: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a specific drive."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request("GET", f"/sites/{site_id}/drives/{drive_id}", params=params)

    @requires_capability(SharePointCapability.DRIVES_READ)
    def list_items(
        self,
        site_id: str,
        drive_id: str,
        query: DriveItemsQuery | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List items in a drive."""
        current = query or DriveItemsQuery()
        return self._list_folder(
            site_id,
            drive_id,
            folder_path=current.folder_path,
            select_fields=current.select_fields,
            recursive=current.recursive,
        )

    @requires_capability(SharePointCapability.DRIVES_READ)
    def list_items_batched(
        self,
        site_id: str,
        drive_id: str,
        query: DriveItemsQuery | None = None,
    ) -> Generator[builtins.list[dict[str, Any]]]:
        """Yield batches of drive items."""
        current = query or DriveItemsQuery()
        batch_size = current.batch_size or 200
        batch: list[dict[str, Any]] = []

        for item in self._walk(
            site_id,
            drive_id,
            folder_path=current.folder_path,
            select_fields=current.select_fields,
            recursive=current.recursive,
        ):
            batch.append(item)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    @requires_capability(SharePointCapability.DRIVES_READ)
    def get_item(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single drive item by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}",
            params=params,
        )

    @requires_capability(SharePointCapability.DRIVES_READ)
    def get_item_by_path(
        self,
        site_id: str,
        drive_id: str,
        file_path: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a drive item by path relative to root."""
        path = file_path.strip("/")
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/root:/{path}",
            params=params,
        )

    @requires_capability(SharePointCapability.DRIVES_READ)
    def download(self, site_id: str, drive_id: str, item_id: str) -> bytes:
        """Download a file by item ID."""
        return self._http.request_raw(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/content",
        )

    @requires_capability(SharePointCapability.DRIVES_READ)
    def download_by_path(
        self,
        site_id: str,
        drive_id: str,
        file_path: str,
    ) -> bytes:
        """Download a file by path relative to root."""
        path = file_path.strip("/")
        return self._http.request_raw("GET", f"/sites/{site_id}/drives/{drive_id}/root:/{path}:/content")

    @requires_capability(SharePointCapability.DRIVES_READ)
    def search(
        self,
        site_id: str,
        drive_id: str,
        query: DriveSearchQuery | None = None,
    ) -> PagedResult:
        """Search for items within a drive."""
        current = query or DriveSearchQuery()

        params: dict[str, Any] = {"$top": current.top}
        if current.skip:
            params["$skip"] = current.skip
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/root/search(q='{current.query}')",
            params=params,
        )
        return build_paged_result(data, current.top, current.skip)

    @requires_capability(SharePointCapability.DRIVES_READ)
    def search_all(
        self,
        site_id: str,
        drive_id: str,
        query: DriveSearchQuery | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """Search within a drive, auto-following pagination."""
        current = query or DriveSearchQuery()

        params: dict[str, Any] = {"$top": current.top}
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)

        data = self._http.request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/root/search(q='{current.query}')",
            params=params,
        )

        items: list[dict[str, Any]] = data.get("value", [])
        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        return items

    @requires_capability(SharePointCapability.DRIVES_READ)
    def get_delta(
        self,
        site_id: str,
        drive_id: str,
        query: DeltaQuery | None = None,
    ) -> dict[str, Any]:
        """Get incremental changes (delta sync)."""
        current = query or DeltaQuery()

        if current.delta_token:
            return self._http.request_url("GET", current.delta_token)

        params = None
        if current.select_fields:
            params = {"$select": ",".join(current.select_fields)}

        return self._http.request(
            "GET",
            f"/sites/{site_id}/drives/{drive_id}/root/delta",
            params=params,
        )

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def upload(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str,
        upload_file: UploadFile,
    ) -> dict[str, Any]:
        """Upload a small file (<=4 MB)."""
        file_name = upload_file.file_path.replace("\\", "/").split("/")[-1]
        item_path = self._build_item_path(folder_path, file_name)

        target = f"/sites/{site_id}/drives/{drive_id}/{item_path}:/content"
        url = f"{GRAPH_BASE_URL}{target}"

        return self._http.upload_bytes(
            url,
            data=upload_file.content,
            content_type=upload_file.content_type,
        )

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def upload_large(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str,
        upload_file: UploadFile,
        chunk_size: int = 10 * 1024 * 1024,
    ) -> dict[str, Any]:
        """Upload a large file via upload session."""
        file_name = upload_file.file_path.replace("\\", "/").split("/")[-1]
        item_path = self._build_item_path(folder_path, file_name)

        session = self._http.request(
            "POST",
            f"/sites/{site_id}/drives/{drive_id}/{item_path}:/createUploadSession",
            json_body={
                "item": {
                    "@microsoft.graph.conflictBehavior": (upload_file.conflict_behavior),
                    "name": file_name,
                }
            },
        )
        upload_url = session["uploadUrl"]

        data = upload_file.content
        total = len(data)
        start = 0
        result: dict[str, Any] = {}

        while start < total:
            end = min(start + chunk_size, total)
            chunk = data[start:end]

            headers = {
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end - 1}/{total}",
            }

            response = requests.put(
                upload_url,
                headers=headers,
                data=chunk,
                timeout=300,
            )
            response.raise_for_status()

            if response.content:
                result = response.json()

            start = end

        return result

    @staticmethod
    def _build_item_path(folder_path: str, file_name: str) -> str:
        """Build Graph root item path for upload operations."""
        path = folder_path.strip("/")
        if path:
            return f"root:/{path}/{file_name}"
        return f"root:/{file_name}"

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def create_folder(
        self,
        site_id: str,
        drive_id: str,
        parent_path: str,
        folder_name: str,
    ) -> dict[str, Any]:
        """Create a folder in the drive."""
        path = parent_path.strip("/")
        parent = (
            f"/sites/{site_id}/drives/{drive_id}/root:/{path}:/children"
            if path
            else f"/sites/{site_id}/drives/{drive_id}/root/children"
        )

        return self._http.request(
            "POST",
            parent,
            json_body={
                "name": folder_name,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "rename",
            },
        )

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def delete(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
    ) -> None:
        """Delete a drive item."""
        self._http.request("DELETE", f"/sites/{site_id}/drives/{drive_id}/items/{item_id}")

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def copy(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        target_parent_id: str,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Copy a drive item."""
        body: dict[str, Any] = {"parentReference": {"id": target_parent_id}}
        if new_name:
            body["name"] = new_name

        return self._http.request(
            "POST",
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}/copy",
            json_body=body,
        )

    @requires_capability(SharePointCapability.DRIVES_WRITE)
    def move(
        self,
        site_id: str,
        drive_id: str,
        item_id: str,
        target_parent_id: str,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        """Move a drive item."""
        body: dict[str, Any] = {"parentReference": {"id": target_parent_id}}
        if new_name:
            body["name"] = new_name

        return self._http.request(
            "PATCH",
            f"/sites/{site_id}/drives/{drive_id}/items/{item_id}",
            json_body=body,
        )

    def _list_folder(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "",
        select_fields: builtins.list[str] | None = None,
        recursive: bool = False,
    ) -> builtins.list[dict[str, Any]]:
        """List items in a folder, optionally recursive."""
        return list(
            self._walk(
                site_id,
                drive_id,
                folder_path=folder_path,
                select_fields=select_fields,
                recursive=recursive,
            )
        )

    def _walk(
        self,
        site_id: str,
        drive_id: str,
        folder_path: str = "",
        select_fields: builtins.list[str] | None = None,
        recursive: bool = False,
    ) -> Generator[dict[str, Any]]:
        """Walk a folder structure and yield items."""
        base = f"/sites/{site_id}/drives/{drive_id}"
        path = folder_path.strip("/")

        endpoint = f"{base}/root:/{path}:/children" if path else f"{base}/root/children"

        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        data = self._http.request("GET", endpoint, params=params)
        items: list[dict[str, Any]] = data.get("value", [])

        while "@odata.nextLink" in data:
            data = self._http.request_url("GET", data["@odata.nextLink"])
            items.extend(data.get("value", []))

        for item in items:
            yield item

            if recursive and "folder" in item:
                child_path = get_folder_path(item)
                name = item.get("name", "")
                sub_path = f"{child_path}/{name}" if child_path else name

                yield from self._walk(
                    site_id,
                    drive_id,
                    folder_path=sub_path,
                    select_fields=select_fields,
                    recursive=True,
                )


__all__ = ["DriveService"]
