"""Client errors — typed exceptions for unified-ui API interactions."""

from __future__ import annotations


class ClientError(Exception):
    """Base exception for all unified-ui client errors."""

    def __init__(self, message: str) -> None:
        """Initialize the client error.

        Args:
            message: Human-readable error description.
        """
        super().__init__(message)
        self.message = message


class APIError(ClientError):
    """Error returned by the unified-ui agent service API.

    Attributes:
        status_code: HTTP status code from the response.
        response_body: Raw response body text.
    """

    def __init__(self, status_code: int, message: str, response_body: str = "") -> None:
        """Initialize the API error.

        Args:
            status_code: HTTP status code from the response.
            message: Human-readable error description.
            response_body: Raw response body text.
        """
        super().__init__(f"[{status_code}] {message}")
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(APIError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed", response_body: str = "") -> None:
        """Initialize the authentication error.

        Args:
            message: Human-readable error description.
            response_body: Raw response body text.
        """
        super().__init__(status_code=401, message=message, response_body=response_body)


class NotFoundError(APIError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found", response_body: str = "") -> None:
        """Initialize the not found error.

        Args:
            message: Human-readable error description.
            response_body: Raw response body text.
        """
        super().__init__(status_code=404, message=message, response_body=response_body)


class ValidationError(APIError):
    """Raised when the request fails validation (400/422)."""

    def __init__(self, message: str = "Validation failed", response_body: str = "") -> None:
        """Initialize the validation error.

        Args:
            message: Human-readable error description.
            response_body: Raw response body text.
        """
        super().__init__(status_code=400, message=message, response_body=response_body)


class ConflictError(APIError):
    """Raised when a conflict occurs (409), e.g. duplicate trace for a conversation."""

    def __init__(self, message: str = "Resource conflict", response_body: str = "") -> None:
        """Initialize the conflict error.

        Args:
            message: Human-readable error description.
            response_body: Raw response body text.
        """
        super().__init__(status_code=409, message=message, response_body=response_body)
