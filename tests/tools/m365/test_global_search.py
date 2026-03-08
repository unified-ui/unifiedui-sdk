"""Tests for M365 Global Search client."""

from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.tools.m365.global_search import (
    BatchSearchQuery,
    EntityType,
    GraphSearchClient,
    SearchRequest,
)


class TestGraphSearchClient:
    """Tests for GraphSearchClient class."""

    @pytest.fixture()
    def mock_auth(self) -> MagicMock:
        """Create mock auth provider."""
        mock = MagicMock()
        mock.get_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        }
        return mock

    def test_client_initialization(self, mock_auth: MagicMock) -> None:
        """Initialize GraphSearchClient."""
        client = GraphSearchClient(mock_auth)

        assert client.search is not None

    def test_search_service_exists(self, mock_auth: MagicMock) -> None:
        """Search service is accessible."""
        client = GraphSearchClient(mock_auth)

        assert hasattr(client, "search")


class TestEntityType:
    """Tests for EntityType enum."""

    def test_all_entity_types(self) -> None:
        """Verify all entity types are defined."""
        assert EntityType.MESSAGE.value == "message"
        assert EntityType.EVENT.value == "event"
        assert EntityType.DRIVE_ITEM.value == "driveItem"
        assert EntityType.LIST_ITEM.value == "listItem"
        assert EntityType.SITE.value == "site"
        assert EntityType.LIST.value == "list"

    def test_entity_type_is_string(self) -> None:
        """Entity types are string-based."""
        assert isinstance(EntityType.MESSAGE.value, str)


class TestSearchRequest:
    """Tests for SearchRequest dataclass."""

    def test_required_fields(self) -> None:
        """SearchRequest requires query and entity_types."""
        request = SearchRequest(
            query="test",
            entity_types=[EntityType.MESSAGE],
        )

        assert request.query == "test"
        assert request.entity_types == [EntityType.MESSAGE]

    def test_defaults(self) -> None:
        """SearchRequest with default values."""
        request = SearchRequest(
            query="test",
            entity_types=[EntityType.MESSAGE],
        )

        assert request.top == 25
        assert request.skip == 0
        assert request.select_fields is None

    def test_custom_fields(self) -> None:
        """SearchRequest with custom fields."""
        request = SearchRequest(
            query="custom",
            entity_types=[EntityType.DRIVE_ITEM],
            top=50,
            skip=10,
            select_fields=["id", "name"],
        )

        assert request.top == 50
        assert request.skip == 10
        assert request.select_fields == ["id", "name"]

    def test_multiple_entity_types(self) -> None:
        """SearchRequest with multiple entity types."""
        request = SearchRequest(
            query="report",
            entity_types=[EntityType.DRIVE_ITEM, EntityType.LIST_ITEM],
        )

        assert len(request.entity_types) == 2


class TestBatchSearchQuery:
    """Tests for BatchSearchQuery dataclass."""

    def test_batch_creation(self) -> None:
        """Create batch with multiple requests."""
        batch = BatchSearchQuery(
            requests=[
                SearchRequest(
                    query="query1", entity_types=[EntityType.MESSAGE]
                ),
                SearchRequest(query="query2", entity_types=[EntityType.EVENT]),
            ]
        )

        assert len(batch.requests) == 2
        assert batch.requests[0].query == "query1"
        assert batch.requests[1].query == "query2"
