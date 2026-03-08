"""Tests for M365 SharePoint client."""

from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.tools.m365.sharepoint import (
    CreateListItem,
    DriveItemsQuery,
    ListItemsQuery,
    PagesQuery,
    SearchQuery,
    SharePointAPIClient,
    SharePointCapability,
    SiteSearchQuery,
    UpdateListItem,
    UploadFile,
)
from unifiedui_sdk.tools.m365.sharepoint.exceptions import SharePointCapabilityError


class TestSharePointAPIClient:
    """Tests for SharePointAPIClient class."""

    @pytest.fixture()
    def mock_auth(self) -> MagicMock:
        """Create mock auth provider."""
        mock = MagicMock()
        mock.get_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        }
        return mock

    @pytest.fixture()
    def full_client(self, mock_auth: MagicMock) -> SharePointAPIClient:
        """Create client with all capabilities."""
        return SharePointAPIClient(mock_auth)

    @pytest.fixture()
    def readonly_client(self, mock_auth: MagicMock) -> SharePointAPIClient:
        """Create client with read-only capabilities."""
        return SharePointAPIClient(
            mock_auth,
            capabilities=[
                SharePointCapability.SITES_READ,
                SharePointCapability.DRIVES_READ,
            ],
        )

    def test_enabled_capabilities_default(
        self, full_client: SharePointAPIClient
    ) -> None:
        """All capabilities enabled by default."""
        caps = full_client.enabled_capabilities
        assert SharePointCapability.SITES_READ in caps
        assert SharePointCapability.DRIVES_WRITE in caps
        assert SharePointCapability.LISTS_WRITE in caps

    def test_enabled_capabilities_restricted(
        self, readonly_client: SharePointAPIClient
    ) -> None:
        """Only specified capabilities enabled."""
        caps = readonly_client.enabled_capabilities
        assert SharePointCapability.SITES_READ in caps
        assert SharePointCapability.DRIVES_WRITE not in caps

    def test_services_exist(self, full_client: SharePointAPIClient) -> None:
        """Client has expected services."""
        assert hasattr(full_client, "sites")
        assert hasattr(full_client, "drives")
        assert hasattr(full_client, "pages")
        assert hasattr(full_client, "lists")
        assert hasattr(full_client, "onenote")
        assert hasattr(full_client, "search")

    def test_capability_enforcement(
        self, readonly_client: SharePointAPIClient
    ) -> None:
        """Capability enforcement blocks write operations."""
        with pytest.raises(SharePointCapabilityError):
            readonly_client.drives.upload(
                "site",
                "drive",
                "/folder",
                UploadFile(file_path="test.txt", content=b"data"),
            )


class TestSharePointCapability:
    """Tests for SharePointCapability enum."""

    def test_all_capabilities(self) -> None:
        """Verify all capabilities are defined."""
        assert SharePointCapability.SITES_READ.value == "sites_read"
        assert SharePointCapability.DRIVES_READ.value == "drives_read"
        assert SharePointCapability.DRIVES_WRITE.value == "drives_write"
        assert SharePointCapability.PAGES_READ.value == "pages_read"
        assert SharePointCapability.LISTS_READ.value == "lists_read"
        assert SharePointCapability.LISTS_WRITE.value == "lists_write"
        assert SharePointCapability.ONENOTE_READ.value == "onenote_read"
        assert SharePointCapability.SEARCH.value == "search"


class TestSharePointModels:
    """Tests for SharePoint model dataclasses."""

    def test_site_search_query_defaults(self) -> None:
        """SiteSearchQuery default values."""
        query = SiteSearchQuery()

        assert query.top == 25
        assert query.keyword == ""

    def test_site_search_query_custom(self) -> None:
        """SiteSearchQuery with custom values."""
        query = SiteSearchQuery(keyword="marketing", top=50)

        assert query.keyword == "marketing"
        assert query.top == 50

    def test_drive_items_query(self) -> None:
        """DriveItemsQuery configuration."""
        query = DriveItemsQuery(
            folder_path="/Reports",
            recursive=True,
            select_fields=["id", "name"],
        )

        assert query.folder_path == "/Reports"
        assert query.recursive is True
        assert query.select_fields == ["id", "name"]

    def test_drive_items_query_defaults(self) -> None:
        """DriveItemsQuery default values."""
        query = DriveItemsQuery()

        assert query.folder_path == ""
        assert query.recursive is False

    def test_upload_file(self) -> None:
        """UploadFile dataclass."""
        upload = UploadFile(
            file_path="report.pdf",
            content=b"PDF content",
            content_type="application/pdf",
        )

        assert upload.file_path == "report.pdf"
        assert upload.content == b"PDF content"
        assert upload.conflict_behavior == "rename"

    def test_pages_query(self) -> None:
        """PagesQuery configuration."""
        query = PagesQuery(
            top=50,
            skip=10,
            filter="promotedState eq 1",
        )

        assert query.top == 50
        assert query.filter == "promotedState eq 1"

    def test_list_items_query(self) -> None:
        """ListItemsQuery configuration."""
        query = ListItemsQuery(
            top=100,
            filter="fields/Status eq 'Active'",
            expand="fields",
        )

        assert query.top == 100
        assert query.expand == "fields"

    def test_create_list_item(self) -> None:
        """CreateListItem dataclass."""
        item = CreateListItem(fields={"Title": "New Task", "Priority": "High"})

        assert item.fields["Title"] == "New Task"
        assert item.fields["Priority"] == "High"

    def test_update_list_item(self) -> None:
        """UpdateListItem dataclass."""
        item = UpdateListItem(fields={"Status": "Completed"})

        assert item.fields["Status"] == "Completed"

    def test_search_query(self) -> None:
        """SearchQuery configuration."""
        query = SearchQuery(
            query="quarterly report",
            entity_types=["driveItem", "listItem"],
            top=50,
        )

        assert query.query == "quarterly report"
        assert query.entity_types == ["driveItem", "listItem"]
        assert query.top == 50
