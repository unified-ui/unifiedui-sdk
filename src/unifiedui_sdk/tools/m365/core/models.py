"""Shared data models for M365 Graph clients."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class PagedResult:
    """Paginated response wrapper for AI/RAG workflows.

    Attributes:
        value: The items in the current page.
        top: Maximum items requested per page.
        skip: Offset of the current page.
        has_more: Whether additional pages are available.
        total_count: Total items (only when Graph returns
            ``@odata.count``; ``None`` otherwise).
    """

    value: list[dict] = field(default_factory=list)
    top: int = 0
    skip: int = 0
    has_more: bool = False
    total_count: int | None = None


def build_paged_result(
    data: dict,
    top: int,
    skip: int,
) -> PagedResult:
    """Build a ``PagedResult`` from a Graph API response dict.

    Detects ``@odata.nextLink`` for ``has_more`` and reads
    ``@odata.count`` when present.
    """
    return PagedResult(
        value=data.get("value", []),
        top=top,
        skip=skip,
        has_more="@odata.nextLink" in data,
        total_count=data.get("@odata.count"),
    )


__all__ = ["PagedResult", "build_paged_result"]
