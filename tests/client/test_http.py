"""Tests for HTTP transport layer."""

from __future__ import annotations

import json
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.client.config import ClientConfig
from unifiedui_sdk.client.errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from unifiedui_sdk.client.http import HTTPTransport


def _make_config(**overrides: Any) -> ClientConfig:
    """Create a test ClientConfig with sensible defaults."""
    defaults: dict[str, Any] = {
        "base_url": "https://api.test.com",
        "tenant_id": "t-1",
        "bearer_token": "test-token",
    }
    defaults.update(overrides)
    return ClientConfig(**defaults)


def _mock_response(status: int = 200, body: dict[str, Any] | str = "") -> MagicMock:
    """Create a mock HTTP response for urlopen."""
    mock = MagicMock()
    mock.status = status
    if isinstance(body, dict):
        mock.read.return_value = json.dumps(body).encode("utf-8")
    else:
        mock.read.return_value = body.encode("utf-8") if body else b""
    mock.__enter__ = lambda s: s
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def _mock_http_error(status: int, body: str = "") -> urllib.error.HTTPError:
    """Create a mock HTTPError."""
    err = urllib.error.HTTPError(
        url="https://api.test.com/test",
        code=status,
        msg=f"HTTP {status}",
        hdrs=None,  # type: ignore[arg-type]
        fp=None,
    )
    err.read = MagicMock(return_value=body.encode("utf-8"))  # type: ignore[assignment]
    return err


class TestHTTPTransportBuildHeaders:
    """Tests for header construction."""

    def test_includes_content_type(self) -> None:
        transport = HTTPTransport(_make_config())
        headers = transport._build_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_includes_auth_headers(self) -> None:
        transport = HTTPTransport(_make_config(bearer_token="my-tok"))
        headers = transport._build_headers()
        assert headers["Authorization"] == "Bearer my-tok"

    def test_includes_default_headers(self) -> None:
        transport = HTTPTransport(_make_config(default_headers={"X-Custom": "val"}))
        headers = transport._build_headers()
        assert headers["X-Custom"] == "val"

    def test_extra_headers_override(self) -> None:
        transport = HTTPTransport(_make_config())
        headers = transport._build_headers(extra={"Accept": "text/plain"})
        assert headers["Accept"] == "text/plain"


class TestHTTPTransportRequest:
    """Tests for the request method."""

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_get_request_returns_json(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(200, {"id": "abc"})
        transport = HTTPTransport(_make_config())

        result = transport.request("GET", "/test")
        assert result == {"id": "abc"}

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_post_request_sends_body(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(201, {"id": "new-id"})
        transport = HTTPTransport(_make_config())

        result = transport.request("POST", "/test", body={"key": "value"})
        assert result == {"id": "new-id"}

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.data == json.dumps({"key": "value"}).encode("utf-8")

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_204_returns_empty_dict(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(204)
        transport = HTTPTransport(_make_config())

        result = transport.request("DELETE", "/test")
        assert result == {}

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_request_uses_correct_url(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _mock_response(200, {})
        transport = HTTPTransport(_make_config())

        transport.request("GET", "/tenants/t-1/traces")

        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.full_url == "https://api.test.com/api/v1/agent-service/tenants/t-1/traces"


class TestHTTPTransportErrorMapping:
    """Tests for error mapping from HTTP status codes."""

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_401_raises_authentication_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(401, '{"error":"unauthorized"}')
        transport = HTTPTransport(_make_config())

        with pytest.raises(AuthenticationError) as exc_info:
            transport.request("GET", "/test")
        assert exc_info.value.status_code == 401

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_404_raises_not_found_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(404, '{"error":"not found"}')
        transport = HTTPTransport(_make_config())

        with pytest.raises(NotFoundError):
            transport.request("GET", "/test")

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_400_raises_validation_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(400, '{"error":"bad request"}')
        transport = HTTPTransport(_make_config())

        with pytest.raises(ValidationError):
            transport.request("POST", "/test", body={})

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_409_raises_conflict_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(409, '{"error":"conflict"}')
        transport = HTTPTransport(_make_config())

        with pytest.raises(ConflictError):
            transport.request("POST", "/test", body={})

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_500_raises_api_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(500, '{"error":"server error"}')
        transport = HTTPTransport(_make_config())

        with pytest.raises(APIError) as exc_info:
            transport.request("GET", "/test")
        assert exc_info.value.status_code == 500

    @patch("unifiedui_sdk.client.http.urlopen")
    def test_error_with_plain_text_body(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = _mock_http_error(502, "Bad Gateway")
        transport = HTTPTransport(_make_config())

        with pytest.raises(APIError) as exc_info:
            transport.request("GET", "/test")
        assert "Bad Gateway" in str(exc_info.value)


class TestExtractErrorMessage:
    """Tests for the static error message extraction helper."""

    def test_extracts_error_field(self) -> None:
        msg = HTTPTransport._extract_error_message('{"error":"not found"}', 404)
        assert msg == "not found"

    def test_extracts_message_field(self) -> None:
        msg = HTTPTransport._extract_error_message('{"message":"bad input"}', 400)
        assert msg == "bad input"

    def test_falls_back_to_status_code(self) -> None:
        msg = HTTPTransport._extract_error_message("{}", 503)
        assert msg == "HTTP 503"

    def test_non_json_body(self) -> None:
        msg = HTTPTransport._extract_error_message("plain text error", 500)
        assert msg == "plain text error"

    def test_empty_body(self) -> None:
        msg = HTTPTransport._extract_error_message("", 500)
        assert msg == "HTTP 500"
