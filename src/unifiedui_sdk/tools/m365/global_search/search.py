"""Microsoft 365 Global Search service."""

from typing import Any

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.global_search.models import (
    BatchSearchQuery,
    EntityType,
    SearchRequest,
)


class SearchService:
    """Search service wrapping ``POST /search/query``."""

    def __init__(self, http: GraphRequestHandler) -> None:
        """Initialize the search service.

        Args:
            http: HTTP request handler for Graph API.
        """
        self._http = http

    def query(self, request: SearchRequest | None = None) -> list[dict[str, Any]]:
        """Execute a single search request."""
        current = request or SearchRequest()

        data = self._http.request(
            "POST",
            "/search/query",
            json_body={"requests": [self._build(current)]},
        )

        responses = data.get("value", [])
        if not responses:
            return []

        result: list[dict[str, Any]] = responses[0].get("hitsContainers", [])
        return result

    def batch_query(self, batch: BatchSearchQuery) -> list[list[dict[str, Any]]]:
        """Execute a batch with multiple search requests."""
        if not batch.requests:
            return []

        data = self._http.request(
            "POST",
            "/search/query",
            json_body={"requests": [self._build(item) for item in batch.requests]},
        )

        responses: list[dict[str, Any]] = data.get("value", [])
        return [item.get("hitsContainers", []) for item in responses]

    def query_all_pages(
        self,
        request: SearchRequest,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """Auto-paginate through results and return all hits."""
        all_hits: list[dict[str, Any]] = []
        current_skip = request.skip

        for _ in range(max_pages):
            current = SearchRequest(
                query=request.query,
                entity_types=request.entity_types,
                top=request.top,
                skip=current_skip,
                select_fields=request.select_fields,
                sort_by=request.sort_by,
                sort_descending=request.sort_descending,
                region=request.region,
                enable_top_results=request.enable_top_results,
                content_sources=request.content_sources,
            )

            containers = self.query(current)
            if not containers:
                break

            has_more_results = False
            for container in containers:
                all_hits.extend(container.get("hits", []))
                has_more_results = has_more_results or container.get("moreResultsAvailable", False)

            if not has_more_results:
                break

            current_skip += request.top

        return all_hits

    @staticmethod
    def _build(request: SearchRequest) -> dict[str, Any]:
        """Build one request body for Graph search API."""
        entity_types = [entity.value if isinstance(entity, EntityType) else entity for entity in request.entity_types]

        body: dict[str, Any] = {
            "entityTypes": entity_types,
            "query": {"queryString": request.query},
            "from": request.skip,
            "size": request.top,
        }

        if request.select_fields:
            body["fields"] = request.select_fields
        if request.sort_by:
            body["sortProperties"] = [
                {
                    "name": request.sort_by,
                    "isDescending": request.sort_descending,
                }
            ]
        if request.region:
            body["region"] = request.region
        if request.enable_top_results:
            body["enableTopResults"] = True
        if request.content_sources:
            body["contentSources"] = request.content_sources

        return body


__all__ = ["SearchService"]
