"""Data models for Outlook API operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(kw_only=True)
class PaginationQuery:
    """Base for paginated queries."""

    top: int = 25
    skip: int = 0


@dataclass(kw_only=True)
class Recipient:
    """E-mail recipient (address + optional display name)."""

    email: str
    name: str | None = None


@dataclass(kw_only=True)
class FileAttachment:
    """File attachment with base64-encoded content."""

    name: str
    content_bytes: str
    content_type: str = "application/octet-stream"


@dataclass(kw_only=True)
class SendMessage:
    """Parameters for sending an e-mail."""

    to: list[str | Recipient]
    subject: str
    body: str
    cc: list[str | Recipient] | None = None
    bcc: list[str | Recipient] | None = None
    body_type: str = "HTML"
    importance: str = "normal"
    attachments: list[FileAttachment] | None = None
    save_to_sent: bool = True


@dataclass(kw_only=True)
class ReplyMessage:
    """Parameters for replying to an e-mail."""

    body: str
    body_type: str = "HTML"
    reply_all: bool = False


@dataclass(kw_only=True)
class ListMessagesQuery(PaginationQuery):
    """Query parameters for listing messages."""

    folder: str = "inbox"
    filter_query: str | None = None
    search_query: str | None = None
    order_by: str = "receivedDateTime desc"
    select_fields: list[str] | None = None


@dataclass(kw_only=True)
class SearchMessagesQuery(PaginationQuery):
    """Query parameters for KQL message search."""

    query: str
    select_fields: list[str] | None = None


@dataclass(kw_only=True)
class EventAttendee:
    """Calendar event attendee."""

    email: str
    name: str | None = None
    type: str = "required"


@dataclass(kw_only=True)
class EventLocation:
    """Calendar event location."""

    display_name: str


@dataclass(kw_only=True)
class CreateEvent:
    """Parameters for creating a calendar event."""

    subject: str
    start: datetime
    end: datetime
    timezone: str = "UTC"
    body: str | None = None
    body_type: str = "HTML"
    attendees: list[EventAttendee] | None = None
    location: EventLocation | None = None
    is_online: bool = False
    reminder_minutes: int = 15
    recurrence: dict | None = None


@dataclass(kw_only=True)
class UpdateEvent:
    """Parameters for updating a calendar event (partial)."""

    subject: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    timezone: str = "UTC"
    body: str | None = None
    body_type: str = "HTML"
    attendees: list[EventAttendee] | None = None
    location: EventLocation | None = None
    is_online: bool | None = None
    reminder_minutes: int | None = None


@dataclass(kw_only=True)
class ListEventsQuery(PaginationQuery):
    """Query parameters for listing calendar events."""

    start: datetime
    end: datetime
    filter_query: str | None = None
    select_fields: list[str] | None = None
    calendar_id: str | None = None


@dataclass(kw_only=True)
class FreeBusyQuery:
    """Query for checking schedule availability."""

    schedules: list[str]
    start: datetime
    end: datetime
    timezone: str = "UTC"
    availability_view_interval: int = 30


__all__ = [
    "CreateEvent",
    "EventAttendee",
    "EventLocation",
    "FileAttachment",
    "FreeBusyQuery",
    "ListEventsQuery",
    "ListMessagesQuery",
    "PaginationQuery",
    "Recipient",
    "ReplyMessage",
    "SearchMessagesQuery",
    "SendMessage",
    "UpdateEvent",
]
