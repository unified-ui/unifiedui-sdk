"""SharePoint API client."""

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.sharepoint.auth import SharePointAuthProvider
from unifiedui_sdk.tools.m365.sharepoint.capabilities import SharePointCapability
from unifiedui_sdk.tools.m365.sharepoint.drives import DriveService
from unifiedui_sdk.tools.m365.sharepoint.lists import ListService
from unifiedui_sdk.tools.m365.sharepoint.onenote import OneNoteService
from unifiedui_sdk.tools.m365.sharepoint.pages import PageService
from unifiedui_sdk.tools.m365.sharepoint.search import SearchService
from unifiedui_sdk.tools.m365.sharepoint.sites import SiteService


class SharePointAPIClient:
    """Microsoft Graph SharePoint client."""

    def __init__(
        self,
        auth: SharePointAuthProvider,
        capabilities: list[SharePointCapability] | None = None,
    ) -> None:
        """Initialize the SharePoint API client.

        Args:
            auth: Authentication provider for Graph API.
            capabilities: Optional list of enabled capabilities.
                          Defaults to all capabilities.
        """
        self._auth = auth
        self._http = GraphRequestHandler(auth)

        self._capabilities: set[SharePointCapability] = set(
            capabilities if capabilities is not None else list(SharePointCapability)
        )

        self.sites = SiteService(self._http, self._capabilities)
        self.drives = DriveService(self._http, self._capabilities)
        self.pages = PageService(self._http, self._capabilities)
        self.lists = ListService(self._http, self._capabilities)
        self.onenote = OneNoteService(self._http, self._capabilities)
        self.search = SearchService(self._http, self._capabilities)

    @property
    def enabled_capabilities(self) -> set[SharePointCapability]:
        """Return enabled capability set."""
        return self._capabilities.copy()


__all__ = ["SharePointAPIClient"]
