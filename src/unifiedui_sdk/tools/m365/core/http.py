"""Shared authenticated HTTP request handler for Microsoft Graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import requests

from unifiedui_sdk.tools.m365.core.exceptions import M365APIError

if TYPE_CHECKING:
    from unifiedui_sdk.tools.m365.core.auth import GraphAuthProvider

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphRequestHandler:
    """Execute authenticated requests against Graph API."""

    def __init__(self, auth: GraphAuthProvider) -> None:
        """Initialize request handler.

        Args:
            auth: Auth provider used for bearer-token headers.
        """
        self._auth = auth

    @staticmethod
    def _raise_for_error(response: requests.Response) -> None:
        """Raise typed API error for non-2xx responses."""
        if response.ok:
            return

        error_data: dict[str, str] = {}
        try:
            error_data = response.json().get("error", {})
        except Exception:
            error_data = {}

        raise M365APIError(
            status_code=response.status_code,
            error_code=error_data.get("code"),
            message=error_data.get("message", response.text),
        )

    def _send(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> requests.Response:
        """Send authenticated request and raise for Graph API errors."""
        headers = self._auth.get_headers(extra_headers)

        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=json_body,
            timeout=timeout,
        )
        self._raise_for_error(response)
        return response

    @staticmethod
    def _parse_json_response(response: requests.Response) -> dict[str, Any]:
        """Parse JSON response and normalize empty responses to dict."""
        if response.status_code == 204 or not response.content:
            return {}
        result: dict[str, Any] = response.json()
        return result

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute an authenticated request to a Graph path."""
        url = f"{GRAPH_BASE_URL}{path}"
        response = self._send(
            method=method,
            url=url,
            params=params,
            json_body=json_body,
            extra_headers=extra_headers,
            timeout=timeout,
        )
        return self._parse_json_response(response)

    def request_url(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> dict[str, Any]:
        """Execute an authenticated request against full URL."""
        response = self._send(
            method=method,
            url=url,
            params=params,
            json_body=json_body,
            extra_headers=extra_headers,
            timeout=timeout,
        )
        return self._parse_json_response(response)

    def request_raw(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout: int = 60,
    ) -> bytes:
        """Execute request and return raw bytes."""
        url = f"{GRAPH_BASE_URL}{path}"
        response = self._send(
            method=method,
            url=url,
            params=params,
            extra_headers=extra_headers,
            timeout=timeout,
        )
        return response.content

    def upload_bytes(
        self,
        url: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        timeout: int = 120,
    ) -> dict[str, Any]:
        """Upload raw bytes via HTTP PUT."""
        headers = self._auth.get_headers({"Content-Type": content_type})

        response = requests.put(
            url,
            headers=headers,
            data=data,
            timeout=timeout,
        )

        self._raise_for_error(response)

        if not response.content:
            return {}

        result: dict[str, Any] = response.json()
        return result


__all__ = ["GRAPH_BASE_URL", "GraphRequestHandler"]
