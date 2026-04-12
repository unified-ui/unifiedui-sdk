"""Client configuration — settings for connecting to the unified-ui agent service."""

from __future__ import annotations

from dataclasses import dataclass, field

DEFAULT_TIMEOUT = 30.0
DEFAULT_BASE_PATH = "/api/v1/agent-service"


@dataclass(frozen=True)
class ClientConfig:
    """Configuration for the unified-ui agent service client.

    Attributes:
        base_url: Base URL of the agent service (e.g. ``https://agent.unified-ui.com``).
        tenant_id: Tenant identifier for multi-tenant operations.
        bearer_token: OAuth2 bearer token for authentication.
        api_key: Autonomous agent API key (alternative to bearer token).
        timeout: Request timeout in seconds.
        base_path: API version prefix path.
        default_headers: Additional headers to include in every request.
    """

    base_url: str
    tenant_id: str
    bearer_token: str = ""
    api_key: str = ""
    timeout: float = DEFAULT_TIMEOUT
    base_path: str = DEFAULT_BASE_PATH
    default_headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If required fields are missing or no auth is configured.
        """
        if not self.base_url:
            raise ValueError("base_url is required")
        if not self.tenant_id:
            raise ValueError("tenant_id is required")
        if not self.bearer_token and not self.api_key:
            raise ValueError("Either bearer_token or api_key must be provided")

    @property
    def auth_headers(self) -> dict[str, str]:
        """Build authentication headers based on configured credentials.

        Returns:
            Dict with the appropriate authentication header(s).
        """
        headers: dict[str, str] = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        if self.api_key:
            headers["X-Unified-UI-Workflow-API-Key"] = self.api_key
        return headers

    def build_url(self, path: str) -> str:
        """Build a full URL from the base URL, base path, and relative path.

        Args:
            path: Relative API path (e.g. ``/tenants/{tenantId}/traces``).

        Returns:
            Fully qualified URL string.
        """
        base = self.base_url.rstrip("/")
        return f"{base}{self.base_path}{path}"
