"""Tests for the tracing service."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.client.config import ClientConfig
from unifiedui_sdk.client.http import HTTPTransport
from unifiedui_sdk.client.tracing import TracingService
from unifiedui_sdk.tracing.models import (
    NodeData,
    NodeDataIO,
    NodeStatus,
    NodeType,
    Trace,
    TraceContextType,
    TraceNode,
)


@pytest.fixture
def transport() -> MagicMock:
    """Create a mock HTTPTransport with a valid config."""
    mock = MagicMock(spec=HTTPTransport)
    mock.config = ClientConfig(
        base_url="https://api.test.com",
        tenant_id="tenant-42",
        bearer_token="test-token",
    )
    return mock


@pytest.fixture
def service(transport: MagicMock) -> TracingService:
    """Create a TracingService with a mocked transport."""
    return TracingService(transport)


class TestTracingServiceCreateTrace:
    """Tests for TracingService.create_trace."""

    def test_sends_post_request(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {"id": "trace-1"}
        trace = Trace(id="trace-1", tenant_id="tenant-42", context_type=TraceContextType.CONVERSATION)

        result = service.create_trace(trace)

        assert result == "trace-1"
        transport.request.assert_called_once()
        args, kwargs = transport.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/tenants/tenant-42/traces"
        assert kwargs["body"]["id"] == "trace-1"

    def test_returns_id_from_response(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {"id": "server-generated-id"}
        trace = Trace()

        result = service.create_trace(trace)
        assert result == "server-generated-id"

    def test_falls_back_to_trace_id(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {}
        trace = Trace(id="local-id")

        result = service.create_trace(trace)
        assert result == "local-id"

    def test_sends_trace_as_camel_case(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {"id": "t-1"}
        trace = Trace(
            id="t-1",
            tenant_id="tenant-42",
            chat_agent_id="agent-1",
            conversation_id="conv-1",
            context_type=TraceContextType.CONVERSATION,
        )

        service.create_trace(trace)

        body = transport.request.call_args[1]["body"]
        assert "tenantId" in body
        assert "chatAgentId" in body
        assert "conversationId" in body
        assert "contextType" in body

    def test_sends_trace_with_nodes(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {"id": "t-1"}

        node = TraceNode(
            name="llm-call",
            type=NodeType.LLM,
            status=NodeStatus.COMPLETED,
            data=NodeData(
                input=NodeDataIO(text="Hello"),
                output=NodeDataIO(text="World"),
            ),
        )
        trace = Trace(id="t-1", nodes=[node])

        service.create_trace(trace)

        body = transport.request.call_args[1]["body"]
        assert len(body["nodes"]) == 1
        assert body["nodes"][0]["name"] == "llm-call"
        assert body["nodes"][0]["type"] == "llm"


class TestTracingServiceAddNodes:
    """Tests for TracingService.add_nodes."""

    def test_sends_nodes_to_correct_path(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {}

        nodes = [
            TraceNode(name="tool-1", type=NodeType.TOOL, status=NodeStatus.COMPLETED),
            TraceNode(name="tool-2", type=NodeType.TOOL, status=NodeStatus.COMPLETED),
        ]

        service.add_nodes("trace-abc", nodes)

        args, kwargs = transport.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/tenants/tenant-42/traces/trace-abc/nodes"
        assert len(kwargs["body"]["nodes"]) == 2

    def test_serializes_nodes_as_camel_case(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {}

        node = TraceNode(
            name="retriever",
            type=NodeType.RETRIEVER,
            status=NodeStatus.COMPLETED,
            reference_id="ref-1",
        )

        service.add_nodes("trace-1", [node])

        node_data = transport.request.call_args[1]["body"]["nodes"][0]
        assert "referenceId" in node_data


class TestTracingServiceAddLogs:
    """Tests for TracingService.add_logs."""

    def test_sends_logs_to_correct_path(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {}

        service.add_logs("trace-xyz", ["Log entry 1", "Log entry 2"])

        args, kwargs = transport.request.call_args
        assert args[0] == "POST"
        assert args[1] == "/tenants/tenant-42/traces/trace-xyz/logs"
        assert kwargs["body"] == {"logs": ["Log entry 1", "Log entry 2"]}


class TestTracingServiceGetTrace:
    """Tests for TracingService.get_trace."""

    def test_sends_get_request(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {"id": "t-1", "nodes": []}

        result = service.get_trace("t-1")

        args = transport.request.call_args[0]
        assert args[0] == "GET"
        assert args[1] == "/tenants/tenant-42/traces/t-1"
        assert result["id"] == "t-1"


class TestTracingServiceDeleteTrace:
    """Tests for TracingService.delete_trace."""

    def test_sends_delete_request(self, service: TracingService, transport: MagicMock) -> None:
        transport.request.return_value = {}

        service.delete_trace("t-1")

        args = transport.request.call_args[0]
        assert args[0] == "DELETE"
        assert args[1] == "/tenants/tenant-42/traces/t-1"
