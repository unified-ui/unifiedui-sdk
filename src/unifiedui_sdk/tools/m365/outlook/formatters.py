"""Graph API formatting helpers for Outlook models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import datetime

    from unifiedui_sdk.tools.m365.outlook.models import (
        CreateEvent,
        EventAttendee,
        FileAttachment,
        Recipient,
        UpdateEvent,
    )


def format_datetime(dt: datetime, timezone: str) -> dict[str, Any]:
    """Format a datetime for the Graph API."""
    return {
        "dateTime": dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "timeZone": timezone,
    }


def format_recipient(recipient: str | Recipient) -> dict[str, Any]:
    """Convert a recipient to Graph API format."""
    if isinstance(recipient, str):
        return {"emailAddress": {"address": recipient}}
    result: dict[str, Any] = {"emailAddress": {"address": recipient.email}}
    if recipient.name:
        result["emailAddress"]["name"] = recipient.name
    return result


def format_attachment(attachment: FileAttachment) -> dict[str, Any]:
    """Convert an attachment to Graph API format."""
    return {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": attachment.name,
        "contentType": attachment.content_type,
        "contentBytes": attachment.content_bytes,
    }


def format_attendee(attendee: EventAttendee) -> dict[str, Any]:
    """Convert an attendee to Graph API format."""
    address: dict[str, Any] = {"address": attendee.email}
    if attendee.name:
        address["name"] = attendee.name
    return {"emailAddress": address, "type": attendee.type}


def build_event_body(event: CreateEvent) -> dict[str, Any]:
    """Build JSON payload for event creation."""
    body: dict[str, Any] = {
        "subject": event.subject,
        "start": format_datetime(event.start, event.timezone),
        "end": format_datetime(event.end, event.timezone),
        "isOnlineMeeting": event.is_online,
        "reminderMinutesBeforeStart": event.reminder_minutes,
    }

    if event.body:
        body["body"] = {
            "contentType": event.body_type,
            "content": event.body,
        }
    if event.attendees:
        body["attendees"] = [format_attendee(attendee) for attendee in event.attendees]
    if event.location:
        body["location"] = {"displayName": event.location.display_name}
    if event.recurrence:
        body["recurrence"] = event.recurrence

    return body


def build_update_body(event: UpdateEvent) -> dict[str, Any]:
    """Build JSON payload for partial event update."""
    body: dict[str, Any] = {}

    if event.subject is not None:
        body["subject"] = event.subject
    if event.start is not None:
        body["start"] = format_datetime(event.start, event.timezone)
    if event.end is not None:
        body["end"] = format_datetime(event.end, event.timezone)
    if event.body is not None:
        body["body"] = {
            "contentType": event.body_type,
            "content": event.body,
        }
    if event.attendees is not None:
        body["attendees"] = [format_attendee(attendee) for attendee in event.attendees]
    if event.location is not None:
        body["location"] = {"displayName": event.location.display_name}
    if event.is_online is not None:
        body["isOnlineMeeting"] = event.is_online
    if event.reminder_minutes is not None:
        body["reminderMinutesBeforeStart"] = event.reminder_minutes

    return body


__all__ = [
    "build_event_body",
    "build_update_body",
    "format_attachment",
    "format_attendee",
    "format_datetime",
    "format_recipient",
]
