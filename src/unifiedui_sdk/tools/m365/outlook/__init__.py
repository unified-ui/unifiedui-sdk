"""Outlook Graph client package."""

from unifiedui_sdk.tools.m365.outlook.auth import OutlookAuthProvider
from unifiedui_sdk.tools.m365.outlook.capabilities import OutlookCapability
from unifiedui_sdk.tools.m365.outlook.client import OutlookAPIClient
from unifiedui_sdk.tools.m365.outlook.exceptions import (
    OutlookAPIError,
    OutlookAuthError,
    OutlookCapabilityError,
    OutlookClientError,
)
from unifiedui_sdk.tools.m365.outlook.models import (
    CreateEvent,
    EventAttendee,
    EventLocation,
    FileAttachment,
    FreeBusyQuery,
    ListEventsQuery,
    ListMessagesQuery,
    Recipient,
    ReplyMessage,
    SearchMessagesQuery,
    SendMessage,
    UpdateEvent,
)

__all__ = [
    "CreateEvent",
    "EventAttendee",
    "EventLocation",
    "FileAttachment",
    "FreeBusyQuery",
    "ListEventsQuery",
    "ListMessagesQuery",
    "OutlookAPIClient",
    "OutlookAPIError",
    "OutlookAuthError",
    "OutlookAuthProvider",
    "OutlookCapability",
    "OutlookCapabilityError",
    "OutlookClientError",
    "Recipient",
    "ReplyMessage",
    "SearchMessagesQuery",
    "SendMessage",
    "UpdateEvent",
]
