"""Tracing service — trace operations against the unified-ui agent service API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from unifiedui_sdk.client.http import HTTPTransport
    from unifiedui_sdk.tracing.models import Trace, TraceNode


class TracingService:
    """Service for creating and managing traces via the unified-ui agent service.

    Uses the shared ``HTTPTransport`` for all API communication.
    """

    def __init__(self, transport: HTTPTransport) -> None:
        """Initialize the tracing service.

        Args:
            transport: Configured HTTP transport instance.
        """
        self._transport = transport

    def _tenant_path(self, path: str = "") -> str:
        """Build a tenant-scoped API path.

        Args:
            path: Additional path suffix.

        Returns:
            Full tenant-scoped path string.
        """
        tenant_id = self._transport.config.tenant_id
        return f"/tenants/{tenant_id}/traces{path}"

    def create_trace(self, trace: Trace) -> str:
        """Create a new trace in the agent service.

        Args:
            trace: The Trace object to persist.

        Returns:
            The ID of the created trace.

        Raises:
            ValidationError: If the trace data is invalid.
            ConflictError: If a trace already exists for the conversation.
            AuthenticationError: If authentication fails.
            APIError: For other API errors.
        """
        body = trace.to_dict()
        response = self._transport.request("POST", self._tenant_path(), body=body)
        return str(response.get("id", trace.id))

    def add_nodes(self, trace_id: str, nodes: list[TraceNode]) -> None:
        """Append nodes to an existing trace.

        Args:
            trace_id: ID of the target trace.
            nodes: List of TraceNode objects to append.

        Raises:
            NotFoundError: If the trace does not exist.
            AuthenticationError: If authentication fails.
            APIError: For other API errors.
        """
        body: dict[str, Any] = {
            "nodes": [node.to_dict() for node in nodes],
        }
        self._transport.request("POST", self._tenant_path(f"/{trace_id}/nodes"), body=body)

    def add_logs(self, trace_id: str, logs: list[str]) -> None:
        """Append log entries to an existing trace.

        Args:
            trace_id: ID of the target trace.
            logs: List of log message strings to append.

        Raises:
            NotFoundError: If the trace does not exist.
            AuthenticationError: If authentication fails.
            APIError: For other API errors.
        """
        body: dict[str, Any] = {"logs": logs}
        self._transport.request("POST", self._tenant_path(f"/{trace_id}/logs"), body=body)

    def get_trace(self, trace_id: str) -> dict[str, Any]:
        """Retrieve a trace by ID.

        Args:
            trace_id: ID of the trace to retrieve.

        Returns:
            Trace data as a camelCase dict.

        Raises:
            NotFoundError: If the trace does not exist.
            AuthenticationError: If authentication fails.
            APIError: For other API errors.
        """
        return self._transport.request("GET", self._tenant_path(f"/{trace_id}"))

    def delete_trace(self, trace_id: str) -> None:
        """Delete a trace by ID.

        Args:
            trace_id: ID of the trace to delete.

        Raises:
            NotFoundError: If the trace does not exist.
            AuthenticationError: If authentication fails.
            APIError: For other API errors.
        """
        self._transport.request("DELETE", self._tenant_path(f"/{trace_id}"))
