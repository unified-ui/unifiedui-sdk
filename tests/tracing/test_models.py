"""Tests for tracing data models."""

from __future__ import annotations

from datetime import UTC, datetime

from unifiedui_sdk.tracing.models import (
    NodeData,
    NodeDataIO,
    NodeStatus,
    NodeType,
    Trace,
    TraceContextType,
    TraceNode,
)


class TestNodeStatus:
    """Tests for NodeStatus enum."""

    def test_all_values_present(self) -> None:
        expected = {"pending", "running", "completed", "failed", "skipped", "cancelled"}
        assert {s.value for s in NodeStatus} == expected

    def test_string_comparison(self) -> None:
        assert NodeStatus.COMPLETED == "completed"
        assert NodeStatus.FAILED == "failed"


class TestNodeType:
    """Tests for NodeType enum."""

    def test_core_types_present(self) -> None:
        core = {"agent", "tool", "llm", "chain", "retriever", "workflow"}
        values = {t.value for t in NodeType}
        assert core.issubset(values)

    def test_total_count(self) -> None:
        assert len(NodeType) == 22


class TestTraceContextType:
    """Tests for TraceContextType enum."""

    def test_values(self) -> None:
        assert TraceContextType.CONVERSATION == "conversation"
        assert TraceContextType.AUTONOMOUS_AGENT == "autonomous_agent"


class TestNodeDataIO:
    """Tests for NodeDataIO model."""

    def test_defaults(self) -> None:
        io = NodeDataIO()
        assert io.text == ""
        assert io.extra_data == {}
        assert io.metadata == {}

    def test_with_values(self) -> None:
        io = NodeDataIO(text="hello", extra_data={"key": "val"}, metadata={"m": 1})
        assert io.text == "hello"
        assert io.extra_data == {"key": "val"}
        assert io.metadata == {"m": 1}

    def test_camel_case_alias(self) -> None:
        io = NodeDataIO(text="test", extraData={"k": "v"})
        dumped = io.model_dump(by_alias=True)
        assert "extraData" in dumped
        assert dumped["extraData"] == {"k": "v"}


class TestNodeData:
    """Tests for NodeData model."""

    def test_defaults(self) -> None:
        data = NodeData()
        assert data.input is None
        assert data.output is None

    def test_with_io(self) -> None:
        data = NodeData(
            input=NodeDataIO(text="in"),
            output=NodeDataIO(text="out"),
        )
        assert data.input is not None
        assert data.input.text == "in"
        assert data.output is not None
        assert data.output.text == "out"


class TestTraceNode:
    """Tests for TraceNode model."""

    def test_creation_with_defaults(self) -> None:
        node = TraceNode(name="test", type=NodeType.LLM)
        assert node.name == "test"
        assert node.type == NodeType.LLM
        assert node.status == NodeStatus.PENDING
        assert node.duration == 0.0
        assert node.nodes == []
        assert node.logs == []
        assert node.id  # should have auto-generated UUID

    def test_mark_running(self) -> None:
        node = TraceNode(name="test", type=NodeType.TOOL)
        node.mark_running()
        assert node.status == NodeStatus.RUNNING
        assert node.start_at is not None

    def test_mark_completed(self) -> None:
        node = TraceNode(name="test", type=NodeType.CHAIN)
        node.mark_running()
        node.mark_completed()
        assert node.status == NodeStatus.COMPLETED
        assert node.end_at is not None
        assert node.duration >= 0.0

    def test_mark_failed_with_error(self) -> None:
        node = TraceNode(name="test", type=NodeType.LLM)
        node.mark_running()
        node.mark_failed(error="Something went wrong")
        assert node.status == NodeStatus.FAILED
        assert "Something went wrong" in node.logs
        assert node.duration >= 0.0

    def test_mark_failed_without_error(self) -> None:
        node = TraceNode(name="test", type=NodeType.LLM)
        node.mark_running()
        node.mark_failed()
        assert node.status == NodeStatus.FAILED
        assert node.logs == []

    def test_add_child(self) -> None:
        parent = TraceNode(name="parent", type=NodeType.CHAIN)
        child = TraceNode(name="child", type=NodeType.LLM)
        parent.add_child(child)
        assert len(parent.nodes) == 1
        assert parent.nodes[0].name == "child"

    def test_recursive_nesting(self) -> None:
        root = TraceNode(name="root", type=NodeType.CHAIN)
        mid = TraceNode(name="mid", type=NodeType.AGENT)
        leaf = TraceNode(name="leaf", type=NodeType.TOOL)
        mid.add_child(leaf)
        root.add_child(mid)
        assert len(root.nodes) == 1
        assert len(root.nodes[0].nodes) == 1
        assert root.nodes[0].nodes[0].name == "leaf"

    def test_to_dict_camel_case(self) -> None:
        node = TraceNode(
            name="test",
            type=NodeType.LLM,
            reference_id="ref-1",
            data=NodeData(input=NodeDataIO(text="hello")),
        )
        d = node.to_dict()
        assert "referenceId" in d
        assert d["name"] == "test"
        assert d["type"] == "llm"
        assert "createdAt" in d
        assert "updatedAt" in d

    def test_to_dict_excludes_none(self) -> None:
        node = TraceNode(name="test", type=NodeType.TOOL)
        d = node.to_dict()
        assert "startAt" not in d
        assert "endAt" not in d


class TestTrace:
    """Tests for Trace model."""

    def test_creation_with_defaults(self) -> None:
        trace = Trace()
        assert trace.id
        assert trace.tenant_id == ""
        assert trace.context_type == TraceContextType.CONVERSATION
        assert trace.nodes == []
        assert trace.logs == []

    def test_creation_with_values(self) -> None:
        trace = Trace(
            tenant_id="t-1",
            chat_agent_id="a-1",
            conversation_id="c-1",
            context_type=TraceContextType.CONVERSATION,
            reference_name="my-workflow",
        )
        assert trace.tenant_id == "t-1"
        assert trace.chat_agent_id == "a-1"
        assert trace.reference_name == "my-workflow"

    def test_add_node(self) -> None:
        trace = Trace()
        node = TraceNode(name="chain", type=NodeType.CHAIN)
        trace.add_node(node)
        assert len(trace.nodes) == 1
        assert trace.nodes[0].name == "chain"

    def test_add_log(self) -> None:
        trace = Trace()
        trace.add_log("hello")
        trace.add_log("world")
        assert trace.logs == ["hello", "world"]

    def test_to_dict_camel_case(self) -> None:
        trace = Trace(
            tenant_id="t-1",
            chat_agent_id="a-1",
            context_type=TraceContextType.CONVERSATION,
        )
        node = TraceNode(name="test", type=NodeType.LLM)
        trace.add_node(node)
        d = trace.to_dict()
        assert "tenantId" in d
        assert "chatAgentId" in d
        assert "contextType" in d
        assert d["contextType"] == "conversation"
        assert len(d["nodes"]) == 1

    def test_to_dict_full_hierarchy(self) -> None:
        trace = Trace(tenant_id="t-1")
        chain = TraceNode(name="chain", type=NodeType.CHAIN)
        llm = TraceNode(name="llm", type=NodeType.LLM)
        tool = TraceNode(name="tool", type=NodeType.TOOL)
        chain.add_child(llm)
        chain.add_child(tool)
        trace.add_node(chain)
        d = trace.to_dict()
        assert len(d["nodes"]) == 1
        assert len(d["nodes"][0]["nodes"]) == 2
        assert d["nodes"][0]["nodes"][0]["type"] == "llm"
        assert d["nodes"][0]["nodes"][1]["type"] == "tool"

    def test_autonomous_agent_context(self) -> None:
        trace = Trace(
            tenant_id="t-1",
            autonomous_agent_id="auto-1",
            context_type=TraceContextType.AUTONOMOUS_AGENT,
        )
        d = trace.to_dict()
        assert d["contextType"] == "autonomous_agent"
        assert d["autonomousAgentId"] == "auto-1"

    def test_populate_by_alias(self) -> None:
        trace = Trace(tenantId="t-alias", chatAgentId="a-alias")
        assert trace.tenant_id == "t-alias"
        assert trace.chat_agent_id == "a-alias"


class TestDurationCalculation:
    """Tests for duration calculation in TraceNode."""

    def test_duration_is_positive(self) -> None:
        node = TraceNode(name="test", type=NodeType.LLM)
        node.start_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        node.mark_completed()
        assert node.duration > 0.0

    def test_duration_zero_when_no_start(self) -> None:
        node = TraceNode(name="test", type=NodeType.LLM)
        node.mark_completed()
        assert node.duration == 0.0
        assert node.start_at is None


class TestRoundTrip:
    """Tests for serialization round-trip."""

    def test_model_dump_and_validate(self) -> None:
        original = TraceNode(
            name="test",
            type=NodeType.LLM,
            status=NodeStatus.COMPLETED,
            data=NodeData(
                input=NodeDataIO(text="in"),
                output=NodeDataIO(text="out", extra_data={"k": "v"}),
            ),
            metadata={"model": "gpt-4"},
        )
        dumped = original.model_dump(by_alias=True)
        restored = TraceNode.model_validate(dumped)
        assert restored.name == original.name
        assert restored.type == original.type
        assert restored.data is not None
        assert restored.data.input is not None
        assert restored.data.input.text == "in"
        assert restored.data.output is not None
        assert restored.data.output.extra_data == {"k": "v"}

    def test_trace_round_trip(self) -> None:
        trace = Trace(tenant_id="t-1", reference_name="wf")
        node = TraceNode(name="n1", type=NodeType.CHAIN)
        node.add_child(TraceNode(name="n2", type=NodeType.TOOL))
        trace.add_node(node)
        dumped = trace.model_dump(by_alias=True)
        restored = Trace.model_validate(dumped)
        assert restored.tenant_id == "t-1"
        assert len(restored.nodes) == 1
        assert len(restored.nodes[0].nodes) == 1
