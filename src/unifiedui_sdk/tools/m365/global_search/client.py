"""Microsoft 365 Global Search client."""

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.global_search.auth import GraphSearchAuthProvider
from unifiedui_sdk.tools.m365.global_search.search import SearchService


class GraphSearchClient:
    """Thin wrapper wiring auth, HTTP handler and search service."""

    def __init__(self, auth: GraphSearchAuthProvider) -> None:
        """Initialize the Graph Search client.

        Args:
            auth: Authentication provider for Graph API.
        """
        self._http = GraphRequestHandler(auth)
        self.search = SearchService(self._http)


__all__ = ["GraphSearchClient"]
