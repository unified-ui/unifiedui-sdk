"""Dataclass models for M365 Global Search queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EntityType(StrEnum):
    """Microsoft Search entity types."""

    DRIVE_ITEM = "driveItem"
    LIST_ITEM = "listItem"
    LIST = "list"
    SITE = "site"
    MESSAGE = "message"
    EVENT = "event"
    CHAT_MESSAGE = "chatMessage"
    PERSON = "person"
    BOOKMARK = "bookmark"
    ACRONYM = "acronym"
    QNA = "qna"
    EXTERNAL_ITEM = "externalItem"


SHAREPOINT_ENTITIES = [
    EntityType.DRIVE_ITEM,
    EntityType.LIST_ITEM,
    EntityType.LIST,
    EntityType.SITE,
]

OUTLOOK_ENTITIES = [EntityType.MESSAGE, EntityType.EVENT]

TEAMS_ENTITIES = [EntityType.CHAT_MESSAGE]

ALL_CONTENT_ENTITIES = [
    EntityType.DRIVE_ITEM,
    EntityType.LIST_ITEM,
    EntityType.LIST,
    EntityType.SITE,
    EntityType.MESSAGE,
    EntityType.EVENT,
    EntityType.CHAT_MESSAGE,
]


@dataclass(kw_only=True)
class SearchRequest:
    """A single search request inside ``POST /search/query``."""

    query: str = ""
    entity_types: list[EntityType | str] = field(default_factory=lambda: list(ALL_CONTENT_ENTITIES))
    top: int = 25
    skip: int = 0
    select_fields: list[str] | None = None
    sort_by: str | None = None
    sort_descending: bool = True
    region: str | None = None
    enable_top_results: bool = False
    content_sources: list[str] | None = None


@dataclass(kw_only=True)
class BatchSearchQuery:
    """Batch query containing multiple search requests."""

    requests: list[SearchRequest] = field(default_factory=list)


__all__ = [
    "ALL_CONTENT_ENTITIES",
    "OUTLOOK_ENTITIES",
    "SHAREPOINT_ENTITIES",
    "TEAMS_ENTITIES",
    "BatchSearchQuery",
    "EntityType",
    "SearchRequest",
]
