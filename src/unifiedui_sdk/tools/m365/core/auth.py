"""Shared authentication provider for Microsoft Graph clients."""

from __future__ import annotations

import time
from typing import Any, ClassVar, Protocol, runtime_checkable

from msal import ConfidentialClientApplication

from unifiedui_sdk.tools.m365.core.exceptions import M365AuthError


@runtime_checkable
class TokenCredential(Protocol):
    """Protocol matching ``azure.identity`` credentials."""

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        """Acquire a token for the given scopes."""
        ...


class GraphAuthProvider:
    """Handle Microsoft Graph authentication with token caching."""

    _SCOPES: ClassVar[list[str]] = ["https://graph.microsoft.com/.default"]

    def __init__(
        self,
        tenant_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        certificate_thumbprint: str | None = None,
        private_key_path: str | None = None,
        credential: TokenCredential | None = None,
    ) -> None:
        """Initialize auth provider.

        Uses either Azure credential injection or MSAL
        client-credential flow (secret or certificate).
        """
        self._access_token: str | None = None
        self._token_expires_at: float = 0

        self._credential: TokenCredential | None = None
        self._msal_app: ConfidentialClientApplication | None = None

        if credential is not None:
            if not isinstance(credential, TokenCredential):
                msg = "credential must implement the TokenCredential protocol (.get_token())."
                raise M365AuthError(msg)
            self._credential = credential
            return

        if not tenant_id or not client_id:
            msg = "tenant_id and client_id are required when not using an Azure credential."
            raise M365AuthError(msg)

        msal_credential = self._build_msal_credential(
            client_secret,
            certificate_thumbprint,
            private_key_path,
        )

        self._msal_app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=msal_credential,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )

    @staticmethod
    def _build_msal_credential(
        client_secret: str | None,
        certificate_thumbprint: str | None,
        private_key_path: str | None,
    ) -> str | dict[str, str]:
        """Build MSAL credential from secret/certificate args."""
        if client_secret:
            return client_secret

        if certificate_thumbprint and private_key_path:
            with open(private_key_path, encoding="utf-8") as file_handle:
                private_key = file_handle.read()
            return {
                "thumbprint": certificate_thumbprint,
                "private_key": private_key,
            }

        msg = "Provide either 'client_secret' or both 'certificate_thumbprint' and 'private_key_path'."
        raise M365AuthError(msg)

    def _is_token_expired(self) -> bool:
        """Check whether the cached token has expired."""
        return time.time() >= self._token_expires_at

    def _get_token_from_credential(self) -> str:
        """Acquire token via Azure Identity credential."""
        if self._credential is None:
            raise M365AuthError("Azure credential is not configured.")

        try:
            token = self._credential.get_token(*self._SCOPES)
        except Exception as exc:
            raise M365AuthError(f"Token acquisition failed: {exc}") from exc

        self._access_token = token.token
        self._token_expires_at = token.expires_on - 60
        return self._access_token

    def _get_token_from_msal(self) -> str:
        """Acquire token via MSAL client credentials."""
        if self._msal_app is None:
            raise M365AuthError("MSAL client is not configured.")

        result = self._msal_app.acquire_token_for_client(
            scopes=self._SCOPES,
        )

        if "access_token" not in result:
            error = result.get(
                "error_description",
                result.get("error", "Unknown error"),
            )
            raise M365AuthError(f"Token acquisition failed: {error}")

        self._access_token = result["access_token"]
        expires_in = result.get("expires_in", 3600)
        self._token_expires_at = time.time() + expires_in - 60
        return self._access_token

    def _get_token(self) -> str:
        """Acquire a new access token."""
        if self._credential is not None:
            return self._get_token_from_credential()
        return self._get_token_from_msal()

    def get_headers(
        self,
        extra_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Return headers with a valid bearer token."""
        if self._access_token is None or self._is_token_expired():
            self._get_token()

        defaults = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

        if extra_headers:
            return defaults | extra_headers

        return defaults


__all__ = ["GraphAuthProvider", "TokenCredential"]
