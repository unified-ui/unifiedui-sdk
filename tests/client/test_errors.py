"""Tests for client error classes."""

from __future__ import annotations

from unifiedui_sdk.client.errors import (
    APIError,
    AuthenticationError,
    ClientError,
    ConflictError,
    NotFoundError,
    ValidationError,
)


class TestClientError:
    """Tests for the base ClientError."""

    def test_message_attribute(self) -> None:
        err = ClientError("something broke")
        assert err.message == "something broke"
        assert str(err) == "something broke"

    def test_inherits_from_exception(self) -> None:
        assert issubclass(ClientError, Exception)


class TestAPIError:
    """Tests for APIError."""

    def test_status_code_in_message(self) -> None:
        err = APIError(status_code=500, message="Internal Server Error")
        assert "500" in str(err)
        assert err.status_code == 500

    def test_response_body_stored(self) -> None:
        err = APIError(status_code=500, message="fail", response_body='{"error":"oops"}')
        assert err.response_body == '{"error":"oops"}'

    def test_inherits_from_client_error(self) -> None:
        assert issubclass(APIError, ClientError)


class TestSpecificErrors:
    """Tests for error subclasses with default status codes."""

    def test_authentication_error(self) -> None:
        err = AuthenticationError()
        assert err.status_code == 401
        assert "Authentication failed" in str(err)

    def test_not_found_error(self) -> None:
        err = NotFoundError()
        assert err.status_code == 404
        assert "not found" in str(err)

    def test_validation_error(self) -> None:
        err = ValidationError()
        assert err.status_code == 400
        assert "Validation" in str(err)

    def test_conflict_error(self) -> None:
        err = ConflictError()
        assert err.status_code == 409
        assert "conflict" in str(err).lower()

    def test_custom_message(self) -> None:
        err = NotFoundError(message="Trace xyz not found")
        assert "Trace xyz not found" in str(err)
        assert err.status_code == 404

    def test_all_inherit_from_api_error(self) -> None:
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(NotFoundError, APIError)
        assert issubclass(ValidationError, APIError)
        assert issubclass(ConflictError, APIError)
