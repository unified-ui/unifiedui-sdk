"""HTTP transport — low-level HTTP request handling for the unified-ui client."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from unifiedui_sdk.client.config import ClientConfig

from unifiedui_sdk.client.errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

_ERROR_MAP: dict[int, type[AuthenticationError | NotFoundError | ValidationError | ConflictError]] = {
    400: ValidationError,
    401: AuthenticationError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
}


class HTTPTransport:
    """Low-level HTTP transport using ``urllib`` (no external dependencies).

    Handles request construction, authentication headers, and error mapping.
    Designed as an internal building block for higher-level service classes.
    """

    def __init__(self, config: ClientConfig) -> None:
        """Initialize the HTTP transport.

        Args:
            config: Client configuration with base URL, auth, and defaults.
        """
        self._config = config

    @property
    def config(self) -> ClientConfig:
        """Return the client configuration."""
        return self._config

    def _build_headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """Build request headers from config defaults, auth, and extras.

        Args:
            extra: Additional headers for a specific request.

        Returns:
            Merged header dictionary.
        """
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self._config.default_headers)
        headers.update(self._config.auth_headers)
        if extra:
            headers.update(extra)
        return headers

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send an HTTP request to the agent service.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: Relative API path (appended to base URL + base path).
            body: Optional JSON request body.
            headers: Optional extra headers for this request.

        Returns:
            Parsed JSON response as a dict. Empty dict for 204 responses.

        Raises:
            APIError: When the API returns a non-2xx status code.
        """
        url = self._config.build_url(path)
        merged_headers = self._build_headers(headers)

        data: bytes | None = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        req = Request(url, data=data, headers=merged_headers, method=method)
        return self._execute(req)

    def _execute(self, req: Request) -> dict[str, Any]:
        """Execute the HTTP request and handle the response.

        Args:
            req: Prepared urllib Request object.

        Returns:
            Parsed JSON response body, or empty dict for no-content responses.

        Raises:
            APIError: Mapped to specific subclass based on status code.
        """
        import urllib.error

        try:
            with urlopen(req, timeout=self._config.timeout) as resp:
                status: int = resp.status
                body_bytes: bytes = resp.read()

                if status == 204 or not body_bytes:
                    return {}

                return json.loads(body_bytes)  # type: ignore[no-any-return]
        except urllib.error.HTTPError as exc:
            status_code: int = exc.code
            response_body = exc.read().decode("utf-8", errors="replace")

            error_message = self._extract_error_message(response_body, status_code)

            error_cls = _ERROR_MAP.get(status_code)
            if error_cls is not None:
                raise error_cls(message=error_message, response_body=response_body) from exc
            raise APIError(
                status_code=status_code,
                message=error_message,
                response_body=response_body,
            ) from exc

    @staticmethod
    def _extract_error_message(response_body: str, status_code: int) -> str:
        """Extract a human-readable error message from the response body.

        Args:
            response_body: Raw response body text.
            status_code: HTTP status code.

        Returns:
            Extracted or fallback error message.
        """
        try:
            data = json.loads(response_body)
            if isinstance(data, dict):
                return str(data.get("error", data.get("message", f"HTTP {status_code}")))
        except (json.JSONDecodeError, ValueError):
            pass
        return f"HTTP {status_code}" if not response_body else response_body[:200]
