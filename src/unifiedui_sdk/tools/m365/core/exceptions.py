"""Common exception hierarchy for Microsoft 365 Graph clients."""


class M365ClientError(Exception):
    """Base exception for M365 Graph client errors."""


class M365AuthError(M365ClientError):
    """Authentication or token acquisition failed."""


class M365CapabilityError(M365ClientError):
    """Operation not available due to disabled capability."""

    def __init__(self, capability: str) -> None:
        """Initialize capability error.

        Args:
            capability: Required capability that is disabled.
        """
        self.capability = capability
        super().__init__(
            f"Capability '{capability}' is not enabled. Add it to the capabilities list in the constructor."
        )


class M365APIError(M365ClientError):
    """Microsoft Graph API returned an error response."""

    def __init__(
        self,
        status_code: int,
        error_code: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize API error.

        Args:
            status_code: HTTP status code.
            error_code: Optional Graph API error code.
            message: Optional error message.
        """
        self.status_code = status_code
        self.error_code = error_code
        self.message = message

        detail = f"[{status_code}]"
        if error_code:
            detail += f" {error_code}"
        if message:
            detail += f": {message}"

        super().__init__(f"Graph API error {detail}")


__all__ = [
    "M365APIError",
    "M365AuthError",
    "M365CapabilityError",
    "M365ClientError",
]
