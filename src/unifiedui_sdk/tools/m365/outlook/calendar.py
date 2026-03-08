"""Calendar service for Outlook API operations."""

from typing import Any

from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler
from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.outlook.capabilities import (
    OutlookCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.outlook.formatters import (
    build_event_body,
    build_update_body,
)
from unifiedui_sdk.tools.m365.outlook.models import (
    CreateEvent,
    FreeBusyQuery,
    ListEventsQuery,
    UpdateEvent,
)


class _CalendarOperations:
    """Core calendar operations (shared by user and ``/me``)."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[OutlookCapability],
    ) -> None:
        self._http = http
        self._capabilities = capabilities

    @requires_capability(OutlookCapability.CALENDAR_READ)
    def list_events(self, base: str, query: ListEventsQuery) -> PagedResult:
        """List events in a time range using calendarView."""
        path = f"{base}/calendars/{query.calendar_id}/calendarView" if query.calendar_id else f"{base}/calendarView"

        params: dict[str, Any] = {
            "startDateTime": query.start.isoformat(),
            "endDateTime": query.end.isoformat(),
            "$top": query.top,
            "$skip": query.skip,
        }
        if query.filter_query:
            params["$filter"] = query.filter_query
        if query.select_fields:
            params["$select"] = ",".join(query.select_fields)

        data = self._http.request("GET", path, params=params)
        return build_paged_result(data, query.top, query.skip)

    @requires_capability(OutlookCapability.CALENDAR_READ)
    def get_event(
        self,
        base: str,
        event_id: str,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Retrieve a single event by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request("GET", f"{base}/events/{event_id}", params=params)

    @requires_capability(OutlookCapability.CALENDAR_READ)
    def get_free_busy(self, base: str, query: FreeBusyQuery) -> list[dict[str, Any]]:
        """Check availability of one or more people."""
        body = {
            "schedules": query.schedules,
            "startTime": {
                "dateTime": query.start.isoformat(),
                "timeZone": query.timezone,
            },
            "endTime": {
                "dateTime": query.end.isoformat(),
                "timeZone": query.timezone,
            },
            "availabilityViewInterval": query.availability_view_interval,
        }

        data = self._http.request("POST", f"{base}/calendar/getSchedule", json_body=body)
        result: list[dict[str, Any]] = data.get("value", [])
        return result

    @requires_capability(OutlookCapability.CALENDAR_WRITE)
    def create_event(self, base: str, event: CreateEvent) -> dict[str, Any]:
        """Create a new calendar event."""
        return self._http.request("POST", f"{base}/events", json_body=build_event_body(event))

    @requires_capability(OutlookCapability.CALENDAR_WRITE)
    def update_event(
        self,
        base: str,
        event_id: str,
        event: UpdateEvent,
    ) -> dict[str, Any]:
        """Update an existing event (partial)."""
        return self._http.request(
            "PATCH",
            f"{base}/events/{event_id}",
            json_body=build_update_body(event),
        )

    @requires_capability(OutlookCapability.CALENDAR_WRITE)
    def delete_event(self, base: str, event_id: str) -> dict[str, Any]:
        """Delete a calendar event."""
        return self._http.request("DELETE", f"{base}/events/{event_id}")


class _MeCalendarService:
    """Calendar operations scoped to ``/me``."""

    def __init__(self, ops: _CalendarOperations) -> None:
        self._ops = ops
        self._capabilities = ops._capabilities

    def list_events(self, query: ListEventsQuery) -> PagedResult:
        """List events for the current user."""
        return self._ops.list_events("/me", query)

    def get_event(
        self,
        event_id: str,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get an event by ID for the current user."""
        return self._ops.get_event("/me", event_id, select_fields)

    def get_free_busy(self, query: FreeBusyQuery) -> list[dict[str, Any]]:
        """Check availability for the current user."""
        return self._ops.get_free_busy("/me", query)

    def create_event(self, event: CreateEvent) -> dict[str, Any]:
        """Create an event for the current user."""
        return self._ops.create_event("/me", event)

    def update_event(self, event_id: str, event: UpdateEvent) -> dict[str, Any]:
        """Update an event for the current user."""
        return self._ops.update_event("/me", event_id, event)

    def delete_event(self, event_id: str) -> dict[str, Any]:
        """Delete an event for the current user."""
        return self._ops.delete_event("/me", event_id)


class CalendarService:
    """Outlook calendar operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[OutlookCapability],
    ) -> None:
        """Initialize the calendar service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._ops = _CalendarOperations(http, capabilities)
        self._capabilities = capabilities
        self.me = _MeCalendarService(self._ops)

    def list_events(self, user: str, query: ListEventsQuery) -> PagedResult:
        """List events for a specific user."""
        return self._ops.list_events(f"/users/{user}", query)

    def get_event(
        self,
        user: str,
        event_id: str,
        select_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get an event by ID for a specific user."""
        return self._ops.get_event(f"/users/{user}", event_id, select_fields)

    def get_free_busy(self, user: str, query: FreeBusyQuery) -> list[dict[str, Any]]:
        """Check availability for a specific user."""
        return self._ops.get_free_busy(f"/users/{user}", query)

    def create_event(self, user: str, event: CreateEvent) -> dict[str, Any]:
        """Create an event for a specific user."""
        return self._ops.create_event(f"/users/{user}", event)

    def update_event(
        self,
        user: str,
        event_id: str,
        event: UpdateEvent,
    ) -> dict[str, Any]:
        """Update an event for a specific user."""
        return self._ops.update_event(f"/users/{user}", event_id, event)

    def delete_event(self, user: str, event_id: str) -> dict[str, Any]:
        """Delete an event for a specific user."""
        return self._ops.delete_event(f"/users/{user}", event_id)


__all__ = ["CalendarService"]
