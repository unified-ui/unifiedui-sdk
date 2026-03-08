"""Tests for M365 core models."""

import pytest

from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result


class TestPagedResult:
    """Tests for PagedResult dataclass."""

    def test_paged_result_creation(self) -> None:
        """Create PagedResult with all fields."""
        result = PagedResult(
            value=[{"id": "1"}, {"id": "2"}],
            top=10,
            skip=0,
            has_more=True,
            total_count=100,
        )

        assert len(result.value) == 2
        assert result.top == 10
        assert result.skip == 0
        assert result.has_more is True
        assert result.total_count == 100

    def test_paged_result_defaults(self) -> None:
        """PagedResult with minimal fields."""
        result = PagedResult(
            value=[],
            top=25,
            skip=0,
            has_more=False,
        )

        assert result.total_count is None

    def test_build_paged_result_with_next_link(self) -> None:
        """Build PagedResult detecting @odata.nextLink."""
        data = {
            "value": [{"id": "1"}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me?$skip=25",
        }

        result = build_paged_result(data, top=25, skip=0)

        assert result.has_more is True
        assert result.value == [{"id": "1"}]

    def test_build_paged_result_without_next_link(self) -> None:
        """Build PagedResult without next link."""
        data = {"value": [{"id": "1"}, {"id": "2"}]}

        result = build_paged_result(data, top=25, skip=0)

        assert result.has_more is False

    def test_build_paged_result_with_count(self) -> None:
        """Build PagedResult with @odata.count."""
        data = {
            "value": [{"id": "1"}],
            "@odata.count": 500,
        }

        result = build_paged_result(data, top=10, skip=0)

        assert result.total_count == 500

    def test_build_paged_result_empty(self) -> None:
        """Build PagedResult from empty response."""
        data: dict = {"value": []}

        result = build_paged_result(data, top=10, skip=0)

        assert result.value == []
        assert result.has_more is False
