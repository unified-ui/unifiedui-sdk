"""Dataclass models for SharePoint API queries."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(kw_only=True)
class PaginationQuery:
    """Base for paginated queries."""

    top: int = 100
    skip: int = 0
    select_fields: list[str] | None = None


@dataclass(kw_only=True)
class SiteSearchQuery(PaginationQuery):
    """Site search query."""

    keyword: str = ""
    top: int = 25


@dataclass(kw_only=True)
class DriveItemsQuery:
    """Query for listing drive items."""

    folder_path: str = ""
    recursive: bool = False
    select_fields: list[str] | None = None
    batch_size: int | None = None


@dataclass(kw_only=True)
class DeltaQuery:
    """Delta-sync query for incremental ingesting."""

    delta_token: str | None = None
    select_fields: list[str] | None = None


@dataclass(kw_only=True)
class DriveSearchQuery:
    """Search within a drive."""

    query: str = ""
    top: int = 25
    skip: int = 0
    select_fields: list[str] | None = None


@dataclass(kw_only=True)
class UploadFile:
    """File upload parameters."""

    file_path: str = ""
    content: bytes = b""
    content_type: str = "application/octet-stream"
    conflict_behavior: str = "rename"


@dataclass(kw_only=True)
class PagesQuery(PaginationQuery):
    """Query for listing site pages."""

    filter: str | None = None
    orderby: str | None = None


@dataclass(kw_only=True)
class ListItemsQuery(PaginationQuery):
    """Query for listing SharePoint list items."""

    filter: str | None = None
    orderby: str | None = None
    expand: str | None = None


@dataclass(kw_only=True)
class CreateListItem:
    """Create a new list item."""

    fields: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class UpdateListItem:
    """Update an existing list item."""

    fields: dict = field(default_factory=dict)


@dataclass(kw_only=True)
class SearchQuery:
    """Microsoft Search API query."""

    query: str = ""
    entity_types: list[str] | None = None
    top: int = 25
    skip: int = 0
    select_fields: list[str] | None = None
    sort_by: str | None = None
    region: str | None = None


__all__ = [
    "CreateListItem",
    "DeltaQuery",
    "DriveItemsQuery",
    "DriveSearchQuery",
    "ListItemsQuery",
    "PagesQuery",
    "PaginationQuery",
    "SearchQuery",
    "SiteSearchQuery",
    "UpdateListItem",
    "UploadFile",
]
