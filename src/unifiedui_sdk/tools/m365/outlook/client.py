"""Outlook API client."""

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.outlook.auth import OutlookAuthProvider
from unifiedui_sdk.tools.m365.outlook.calendar import CalendarService
from unifiedui_sdk.tools.m365.outlook.capabilities import OutlookCapability
from unifiedui_sdk.tools.m365.outlook.messages import MessageService


class OutlookAPIClient:
    """Microsoft Graph Outlook client."""

    def __init__(
        self,
        auth: OutlookAuthProvider,
        capabilities: list[OutlookCapability] | None = None,
    ) -> None:
        """Initialize the Outlook API client.

        Args:
            auth: Authentication provider for Graph API.
            capabilities: Optional list of enabled capabilities.
                          Defaults to all capabilities.
        """
        self._auth = auth
        self._http = GraphRequestHandler(auth)

        self._capabilities: set[OutlookCapability] = set(
            capabilities if capabilities is not None else list(OutlookCapability)
        )

        self.messages = MessageService(self._http, self._capabilities)
        self.calendar = CalendarService(self._http, self._capabilities)

    @property
    def enabled_capabilities(self) -> set[OutlookCapability]:
        """Return enabled capability set."""
        return self._capabilities.copy()


__all__ = ["OutlookAPIClient"]
