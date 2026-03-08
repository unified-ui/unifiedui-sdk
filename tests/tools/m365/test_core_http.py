"""Tests for M365 core HTTP handler."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import requests

from unifiedui_sdk.tools.m365.core.exceptions import M365APIError
from unifiedui_sdk.tools.m365.core.http import GRAPH_BASE_URL, GraphRequestHandler


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(
        self,
        json_data: dict | None = None,
        status_code: int = 200,
        content: bytes = b"",
    ) -> None:
        """Initialize mock response."""
        self._json_data = json_data or {}
        self.status_code = status_code
        self.content = content or b'{}'
        self.ok = status_code < 400
        self.text = str(json_data) if json_data else ""

    def json(self) -> Any:
        """Return JSON data."""
        return self._json_data

    def raise_for_status(self) -> None:
        """Raise on error status."""
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class TestGraphRequestHandler:
    """Tests for GraphRequestHandler class."""

    @pytest.fixture()
    def auth_provider(self) -> MagicMock:
        """Create mock auth provider."""
        mock = MagicMock()
        mock.get_headers.return_value = {
            "Authorization": "Bearer test-access-token",
            "Content-Type": "application/json",
        }
        return mock

    @pytest.fixture()
    def handler(self, auth_provider: MagicMock) -> GraphRequestHandler:
        """Create request handler with mock auth."""
        return GraphRequestHandler(auth_provider)

    def test_request_get(self, handler: GraphRequestHandler) -> None:
        """Execute GET request to Graph API."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse({"value": []})

            result = handler.request("GET", "/me/messages")

            assert result == {"value": []}
            mock_request.assert_called_once()

    def test_request_with_params(self, handler: GraphRequestHandler) -> None:
        """Include query parameters in request."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse({"value": []})

            handler.request(
                "GET", "/me/messages", params={"$top": 10, "$select": "id"}
            )

            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["params"] == {"$top": 10, "$select": "id"}

    def test_request_post_with_json(self, handler: GraphRequestHandler) -> None:
        """Execute POST request with JSON body."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse({"id": "new-id"})

            result = handler.request(
                "POST",
                "/me/messages",
                json_body={"subject": "Test"},
            )

            assert result == {"id": "new-id"}
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["json"] == {"subject": "Test"}

    def test_request_includes_auth_header(
        self, handler: GraphRequestHandler
    ) -> None:
        """Include Authorization header in requests."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse({})

            handler.request("GET", "/me")

            call_kwargs = mock_request.call_args.kwargs
            headers = call_kwargs["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test-access-token"

    def test_request_url_full(self, handler: GraphRequestHandler) -> None:
        """Execute request to full URL."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse({"value": []})
            full_url = "https://graph.microsoft.com/v1.0/me/messages?$skip=10"

            handler.request_url("GET", full_url)

            call_args = mock_request.call_args.args
            assert call_args[1] == full_url

    def test_request_raw_returns_bytes(
        self, handler: GraphRequestHandler
    ) -> None:
        """Return raw bytes from request."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse(
                content=b"file content here"
            )

            result = handler.request_raw("GET", "/me/drive/items/id/content")

            assert result == b"file content here"

    def test_request_error_handling(
        self, handler: GraphRequestHandler
    ) -> None:
        """Raise M365APIError on HTTP error."""
        with patch("requests.request") as mock_request:
            mock_request.return_value = MockResponse(
                json_data={
                    "error": {"code": "NotFound", "message": "Not found"}
                },
                status_code=404,
            )

            with pytest.raises(M365APIError):
                handler.request("GET", "/nonexistent")

    def test_upload_bytes(self, handler: GraphRequestHandler) -> None:
        """Upload bytes to Graph API."""
        with patch("requests.put") as mock_put:
            mock_put.return_value = MockResponse({"id": "uploaded"})

            result = handler.upload_bytes(
                f"{GRAPH_BASE_URL}/me/drive/root:/file.txt:/content",
                data=b"file data",
                content_type="text/plain",
            )

            assert result == {"id": "uploaded"}
            call_kwargs = mock_put.call_args.kwargs
            assert call_kwargs["data"] == b"file data"
