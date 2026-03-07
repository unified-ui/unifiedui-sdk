"""Tests for UnifiedUILanggraphTracer."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from unifiedui_sdk.tracing.langgraph import UnifiedUILanggraphTracer
from unifiedui_sdk.tracing.models import (
    NodeStatus,
    NodeType,
    Trace,
)


def _uuid() -> UUID:
    return uuid4()


def _mock_llm_result(text: str) -> Any:
    mock = MagicMock()
    gen = MagicMock()
    gen.text = text
    mock.generations = [[gen]]
    mock.llm_output = None
    return mock


class TestLanggraphTracerInitialization:
    """Tests for LangGraph tracer creation."""

    def test_default_trace(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        trace = tracer.get_trace()
        assert isinstance(trace, Trace)
        assert trace.nodes == []

    def test_custom_trace(self) -> None:
        custom = Trace(tenant_id="t-1", reference_name="langgraph-test")
        tracer = UnifiedUILanggraphTracer(trace=custom)
        assert tracer.get_trace().tenant_id == "t-1"
        assert tracer.get_trace().reference_name == "langgraph-test"

    def test_trace_property(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        assert tracer.trace is tracer.get_trace()


class TestInternalNodeFiltering:
    """Tests for __start__ and __end__ node filtering."""

    def test_start_node_is_skipped(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        tracer.on_chain_start(
            serialized={},
            inputs={"messages": []},
            run_id=_uuid(),
            name="__start__",
        )
        assert len(tracer.get_trace().nodes) == 0

    def test_end_node_is_skipped(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        tracer.on_chain_start(
            serialized={},
            inputs={},
            run_id=_uuid(),
            name="__end__",
        )
        assert len(tracer.get_trace().nodes) == 0

    def test_start_end_complete_is_noop(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        start_id = _uuid()
        end_id = _uuid()

        tracer.on_chain_start(serialized={}, inputs={}, run_id=start_id, name="__start__")
        tracer.on_chain_end(outputs={}, run_id=start_id)
        tracer.on_chain_start(serialized={}, inputs={}, run_id=end_id, name="__end__")
        tracer.on_chain_end(outputs={}, run_id=end_id)

        assert len(tracer.get_trace().nodes) == 0

    def test_normal_chain_is_not_filtered(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        tracer.on_chain_start(
            serialized={},
            inputs={"messages": []},
            run_id=_uuid(),
            name="agent",
        )
        assert len(tracer.get_trace().nodes) == 1
        assert tracer.get_trace().nodes[0].name == "agent"

    def test_graph_node_names_preserved(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        agent_id = _uuid()
        tools_id = _uuid()

        tracer.on_chain_start(serialized={}, inputs={}, run_id=agent_id, name="agent")
        tracer.on_chain_start(serialized={}, inputs={}, run_id=tools_id, name="tools")

        trace = tracer.get_trace()
        assert len(trace.nodes) == 2
        names = {n.name for n in trace.nodes}
        assert names == {"agent", "tools"}


class TestLanggraphSimulatedWorkflow:
    """Tests simulating realistic LangGraph agent workflows."""

    def test_react_agent_workflow(self) -> None:
        """Simulate create_react_agent: graph -> __start__ -> agent -> tools -> agent -> __end__."""
        tracer = UnifiedUILanggraphTracer()

        # Top-level graph chain
        graph_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={"messages": []}, run_id=graph_id, name="LangGraph")

        # __start__ node (should be filtered)
        start_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=start_id, parent_run_id=graph_id, name="__start__")
        tracer.on_chain_end(outputs={}, run_id=start_id)

        # Agent node
        agent_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=agent_id, parent_run_id=graph_id, name="agent")

        # LLM call inside agent
        llm_id = _uuid()
        msg = MagicMock()
        msg.type = "human"
        msg.content = "What's the weather?"
        tracer.on_chat_model_start(
            serialized={"id": ["langchain", "chat_models", "AzureChatOpenAI"]},
            messages=[[msg]],
            run_id=llm_id,
            parent_run_id=agent_id,
            name="AzureChatOpenAI",
        )
        tracer.on_llm_end(response=_mock_llm_result("tool_call: get_weather"), run_id=llm_id)
        tracer.on_chain_end(outputs={}, run_id=agent_id)

        # Tools node
        tools_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=tools_id, parent_run_id=graph_id, name="tools")

        tool_id = _uuid()
        tracer.on_tool_start(
            serialized={"name": "get_weather"},
            input_str='{"city": "Berlin"}',
            run_id=tool_id,
            parent_run_id=tools_id,
            name="get_weather",
        )
        tracer.on_tool_end(output="Sunny, 22°C", run_id=tool_id)
        tracer.on_chain_end(outputs={}, run_id=tools_id)

        # __end__ node (should be filtered)
        end_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=end_id, parent_run_id=graph_id, name="__end__")
        tracer.on_chain_end(outputs={}, run_id=end_id)

        tracer.on_chain_end(outputs={"messages": ["Sunny"]}, run_id=graph_id)

        # Verify
        trace = tracer.get_trace()
        assert len(trace.nodes) == 1  # Only "LangGraph" at top level
        graph_node = trace.nodes[0]
        assert graph_node.name == "LangGraph"
        assert graph_node.status == NodeStatus.COMPLETED

        # Children: agent, tools (no __start__, __end__)
        child_names = {n.name for n in graph_node.nodes}
        assert "__start__" not in child_names
        assert "__end__" not in child_names
        assert "agent" in child_names
        assert "tools" in child_names
        assert len(graph_node.nodes) == 2

        # Check agent has LLM child
        agent_node = next(n for n in graph_node.nodes if n.name == "agent")
        assert len(agent_node.nodes) == 1
        assert agent_node.nodes[0].name == "AzureChatOpenAI"
        assert agent_node.nodes[0].type == NodeType.LLM

        # Check tools has tool child
        tools_node = next(n for n in graph_node.nodes if n.name == "tools")
        assert len(tools_node.nodes) == 1
        assert tools_node.nodes[0].name == "get_weather"
        assert tools_node.nodes[0].type == NodeType.TOOL
        assert tools_node.nodes[0].status == NodeStatus.COMPLETED


class TestLanggraphCallbackInheritance:
    """Tests verifying inherited callback behavior from BaseTracer."""

    def test_llm_callbacks_work(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "OpenAI"]},
            prompts=["Hello"],
            run_id=run_id,
        )
        tracer.on_llm_end(response=_mock_llm_result("Hi there"), run_id=run_id)

        node = tracer.get_trace().nodes[0]
        assert node.name == "OpenAI"
        assert node.type == NodeType.LLM
        assert node.status == NodeStatus.COMPLETED

    def test_tool_callbacks_work(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_tool_start(
            serialized={"name": "calculator"},
            input_str="2+2",
            run_id=run_id,
        )
        tracer.on_tool_end(output="4", run_id=run_id)

        node = tracer.get_trace().nodes[0]
        assert node.name == "calculator"
        assert node.type == NodeType.TOOL
        assert node.status == NodeStatus.COMPLETED

    def test_error_handling_works(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=run_id, name="agent")
        tracer.on_chain_error(error=RuntimeError("graph failed"), run_id=run_id)

        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.FAILED

    def test_name_from_kwargs_preferred(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["some", "SomeChain"]},
            inputs={},
            run_id=run_id,
            name="my_graph_node",
        )
        assert tracer.get_trace().nodes[0].name == "my_graph_node"

    def test_name_from_serialized_fallback(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "AgentExecutor"]},
            inputs={},
            run_id=run_id,
        )
        assert tracer.get_trace().nodes[0].name == "AgentExecutor"


class TestLanggraphGetTraceDict:
    """Tests for dict serialization from LangGraph tracer."""

    def test_get_trace_dict_returns_dict(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        run_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=run_id, name="agent")
        tracer.on_chain_end(outputs={"result": "done"}, run_id=run_id)

        d = tracer.get_trace_dict()
        assert isinstance(d, dict)
        assert "nodes" in d
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["status"] == "completed"

    def test_filtered_nodes_not_in_dict(self) -> None:
        tracer = UnifiedUILanggraphTracer()

        graph_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=graph_id, name="LangGraph")
        tracer.on_chain_start(serialized={}, inputs={}, run_id=_uuid(), parent_run_id=graph_id, name="__start__")
        tracer.on_chain_start(serialized={}, inputs={}, run_id=_uuid(), parent_run_id=graph_id, name="agent")
        tracer.on_chain_end(outputs={}, run_id=graph_id)

        d = tracer.get_trace_dict()
        graph_children = d["nodes"][0]["nodes"]
        child_names = [n["name"] for n in graph_children]
        assert "__start__" not in child_names
        assert "agent" in child_names


class TestLanggraphEdgeCases:
    """Edge case tests for LangGraph tracer."""

    def test_end_without_start_is_noop(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        tracer.on_chain_end(outputs={}, run_id=_uuid())
        assert len(tracer.get_trace().nodes) == 0

    def test_error_on_filtered_node_is_noop(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        start_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=start_id, name="__start__")
        tracer.on_chain_error(error=RuntimeError("fail"), run_id=start_id)
        assert len(tracer.get_trace().nodes) == 0

    def test_on_text_logs_to_existing_node(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        node_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={}, run_id=node_id, name="agent")
        tracer.on_text("debug info", run_id=_uuid(), parent_run_id=node_id)
        assert "debug info" in tracer.get_trace().nodes[0].logs

    def test_should_trace_node_returns_true_for_regular_names(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        assert tracer._should_trace_node("agent") is True
        assert tracer._should_trace_node("tools") is True
        assert tracer._should_trace_node("LangGraph") is True

    def test_should_trace_node_returns_false_for_internal_nodes(self) -> None:
        tracer = UnifiedUILanggraphTracer()
        assert tracer._should_trace_node("__start__") is False
        assert tracer._should_trace_node("__end__") is False
