"""Tests for M365 core auth module."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.tools.m365.core.auth import GraphAuthProvider
from unifiedui_sdk.tools.m365.core.exceptions import M365AuthError


class MockTokenWithExpiry:
    """Mock token object with required attributes."""

    def __init__(self, token: str, expires_on: float = 9999999999) -> None:
        """Initialize mock token."""
        self.token = token
        self.expires_on = expires_on


class MockCredential:
    """Mock Azure credential implementing TokenCredential protocol."""

    def __init__(self, token: str = "azure-token") -> None:
        """Initialize mock credential."""
        self._token = token

    def get_token(self, *scopes: str, **kwargs: Any) -> MockTokenWithExpiry:
        """Return mock token."""
        return MockTokenWithExpiry(self._token)


class TestGraphAuthProvider:
    """Tests for GraphAuthProvider class."""

    def test_init_with_msal_credentials(self) -> None:
        """Initialize auth provider with MSAL credentials."""
        with patch(
            "unifiedui_sdk.tools.m365.core.auth.ConfidentialClientApplication"
        ) as mock_app:
            mock_app.return_value = MagicMock()

            auth = GraphAuthProvider(
                client_id="test-client-id",
                client_secret="test-secret",
                tenant_id="test-tenant",
            )

            mock_app.assert_called_once()
            assert auth._credential is None

    def test_init_with_token_credential(self) -> None:
        """Initialize auth provider with Azure TokenCredential."""
        mock_credential = MockCredential()

        auth = GraphAuthProvider(credential=mock_credential)

        assert auth._credential is mock_credential
        assert auth._msal_app is None

    def test_init_requires_credentials(self) -> None:
        """Raise error when no credentials provided."""
        with pytest.raises(M365AuthError):
            GraphAuthProvider()

    def test_get_headers_with_msal(self) -> None:
        """Get headers using MSAL flow."""
        with patch(
            "unifiedui_sdk.tools.m365.core.auth.ConfidentialClientApplication"
        ) as mock_cca:
            mock_app = MagicMock()
            mock_app.acquire_token_for_client.return_value = {
                "access_token": "test-token",
                "expires_in": 3600,
            }
            mock_cca.return_value = mock_app

            auth = GraphAuthProvider(
                client_id="test-client-id",
                client_secret="test-secret",
                tenant_id="test-tenant",
            )
            headers = auth.get_headers()

            assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_with_azure_credential(self) -> None:
        """Get headers using Azure TokenCredential."""
        mock_credential = MockCredential("azure-token")

        auth = GraphAuthProvider(credential=mock_credential)
        headers = auth.get_headers()

        assert headers["Authorization"] == "Bearer azure-token"

    def test_get_headers_msal_failure(self) -> None:
        """Raise error when MSAL token acquisition fails."""
        with patch(
            "unifiedui_sdk.tools.m365.core.auth.ConfidentialClientApplication"
        ) as mock_cca:
            mock_app = MagicMock()
            mock_app.acquire_token_for_client.return_value = {
                "error": "invalid_client",
                "error_description": "Bad credentials",
            }
            mock_cca.return_value = mock_app

            auth = GraphAuthProvider(
                client_id="test-client-id",
                client_secret="test-secret",
                tenant_id="test-tenant",
            )

            with pytest.raises(M365AuthError):
                auth.get_headers()

    def test_get_headers_with_extra(self) -> None:
        """Merge extra headers with auth headers."""
        mock_credential = MockCredential()
        auth = GraphAuthProvider(credential=mock_credential)

        headers = auth.get_headers(extra_headers={"X-Custom": "value"})

        assert headers["Authorization"] == "Bearer azure-token"
        assert headers["X-Custom"] == "value"
