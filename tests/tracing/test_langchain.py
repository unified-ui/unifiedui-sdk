"""Tests for UnifiedUILangchainTracer."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from unifiedui_sdk.tracing.langchain import UnifiedUILangchainTracer
from unifiedui_sdk.tracing.models import (
    NodeStatus,
    NodeType,
    Trace,
)


def _uuid() -> UUID:
    return uuid4()


class TestTracerInitialization:
    """Tests for tracer creation."""

    def test_default_trace(self) -> None:
        tracer = UnifiedUILangchainTracer()
        trace = tracer.get_trace()
        assert isinstance(trace, Trace)
        assert trace.nodes == []

    def test_custom_trace(self) -> None:
        custom = Trace(tenant_id="t-1", reference_name="custom")
        tracer = UnifiedUILangchainTracer(trace=custom)
        assert tracer.get_trace().tenant_id == "t-1"
        assert tracer.get_trace().reference_name == "custom"

    def test_trace_property(self) -> None:
        tracer = UnifiedUILangchainTracer()
        assert tracer.trace is tracer.get_trace()


class TestLLMCallbacks:
    """Tests for LLM-related callbacks."""

    def test_on_llm_start_creates_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "AzureChatOpenAI"]},
            prompts=["Hello world"],
            run_id=run_id,
        )
        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        assert trace.nodes[0].name == "AzureChatOpenAI"
        assert trace.nodes[0].type == NodeType.LLM
        assert trace.nodes[0].status == NodeStatus.RUNNING
        assert trace.nodes[0].data is not None
        assert trace.nodes[0].data.input is not None
        assert trace.nodes[0].data.input.text == "Hello world"

    def test_on_llm_start_with_multiple_prompts(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "OpenAI"]},
            prompts=["prompt1", "prompt2"],
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.data is not None
        assert node.data.input is not None
        assert "prompt1" in node.data.input.text
        assert "prompt2" in node.data.input.text

    def test_on_llm_end_completes_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "OpenAI"]},
            prompts=["test"],
            run_id=run_id,
        )

        # Create a mock LLMResult
        from unittest.mock import MagicMock

        mock_result = MagicMock()
        mock_gen = MagicMock()
        mock_gen.text = "Hello! How can I help?"
        mock_result.generations = [[mock_gen]]
        mock_result.llm_output = {"token_usage": {"total_tokens": 50}}

        tracer.on_llm_end(response=mock_result, run_id=run_id)
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None
        assert "Hello! How can I help?" in node.data.output.text
        assert node.duration >= 0.0

    def test_on_llm_error_fails_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "OpenAI"]},
            prompts=["test"],
            run_id=run_id,
        )
        tracer.on_llm_error(
            error=ValueError("API rate limit exceeded"),
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.FAILED
        assert any("rate limit" in log for log in node.logs)


class TestChatModelCallbacks:
    """Tests for chat model callbacks."""

    def test_on_chat_model_start(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()

        from unittest.mock import MagicMock

        msg = MagicMock()
        msg.type = "human"
        msg.content = "Hello"

        tracer.on_chat_model_start(
            serialized={"id": ["langchain", "chat_models", "AzureChatOpenAI"]},
            messages=[[msg]],
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.name == "AzureChatOpenAI"
        assert node.type == NodeType.LLM
        assert node.data is not None
        assert node.data.input is not None
        assert "[human]: Hello" in node.data.input.text


class TestChainCallbacks:
    """Tests for chain-related callbacks."""

    def test_on_chain_start_creates_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "AgentExecutor"]},
            inputs={"input": "test question"},
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.name == "AgentExecutor"
        assert node.type == NodeType.CHAIN
        assert node.status == NodeStatus.RUNNING

    def test_on_chain_end_completes_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Chain"]},
            inputs={"input": "test"},
            run_id=run_id,
        )
        tracer.on_chain_end(
            outputs={"output": "result"},
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None

    def test_on_chain_error_fails_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Chain"]},
            inputs={},
            run_id=run_id,
        )
        tracer.on_chain_error(error=RuntimeError("chain broken"), run_id=run_id)
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.FAILED


class TestToolCallbacks:
    """Tests for tool-related callbacks."""

    def test_on_tool_start_creates_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_tool_start(
            serialized={"name": "get_weather"},
            input_str='{"city": "Berlin"}',
            run_id=run_id,
        )
        node = tracer.get_trace().nodes[0]
        assert node.name == "get_weather"
        assert node.type == NodeType.TOOL
        assert node.data is not None
        assert node.data.input is not None
        assert "Berlin" in node.data.input.text

    def test_on_tool_end_completes_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_tool_start(
            serialized={"name": "calculate"},
            input_str="2+2",
            run_id=run_id,
        )
        tracer.on_tool_end(output="4", run_id=run_id)
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.COMPLETED
        assert node.data is not None
        assert node.data.output is not None
        assert node.data.output.text == "4"

    def test_on_tool_error_fails_node(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_tool_start(
            serialized={"name": "broken_tool"},
            input_str="test",
            run_id=run_id,
        )
        tracer.on_tool_error(error=Exception("tool failed"), run_id=run_id)
        node = tracer.get_trace().nodes[0]
        assert node.status == NodeStatus.FAILED


class TestParentChildRelationships:
    """Tests for hierarchical node nesting."""

    def test_child_node_nested_under_parent(self) -> None:
        tracer = UnifiedUILangchainTracer()
        parent_id = _uuid()
        child_id = _uuid()

        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "AgentExecutor"]},
            inputs={"input": "test"},
            run_id=parent_id,
        )
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "OpenAI"]},
            prompts=["test"],
            run_id=child_id,
            parent_run_id=parent_id,
        )

        trace = tracer.get_trace()
        assert len(trace.nodes) == 1  # only parent at top level
        assert len(trace.nodes[0].nodes) == 1  # child nested
        assert trace.nodes[0].nodes[0].name == "OpenAI"

    def test_multiple_children_under_parent(self) -> None:
        tracer = UnifiedUILangchainTracer()
        parent_id = _uuid()
        child1_id = _uuid()
        child2_id = _uuid()

        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Agent"]},
            inputs={},
            run_id=parent_id,
        )
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "LLM"]},
            prompts=["p1"],
            run_id=child1_id,
            parent_run_id=parent_id,
        )
        tracer.on_tool_start(
            serialized={"name": "tool1"},
            input_str="input",
            run_id=child2_id,
            parent_run_id=parent_id,
        )

        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        assert len(trace.nodes[0].nodes) == 2

    def test_three_level_nesting(self) -> None:
        tracer = UnifiedUILangchainTracer()
        chain_id = _uuid()
        llm_id = _uuid()

        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Chain"]},
            inputs={},
            run_id=chain_id,
        )
        tracer.on_llm_start(
            serialized={"id": ["langchain", "llms", "LLM"]},
            prompts=["test"],
            run_id=llm_id,
            parent_run_id=chain_id,
        )

        trace = tracer.get_trace()
        assert len(trace.nodes) == 1
        chain_node = trace.nodes[0]
        assert len(chain_node.nodes) == 1
        assert chain_node.nodes[0].type == NodeType.LLM


class TestGetTraceDict:
    """Tests for dict serialization via tracer."""

    def test_get_trace_dict_returns_dict(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Chain"]},
            inputs={"input": "test"},
            run_id=run_id,
        )
        tracer.on_chain_end(outputs={"output": "done"}, run_id=run_id)
        d = tracer.get_trace_dict()
        assert isinstance(d, dict)
        assert "nodes" in d
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["status"] == "completed"

    def test_dict_uses_camel_case(self) -> None:
        custom = Trace(tenant_id="t-1", chat_agent_id="a-1")
        tracer = UnifiedUILangchainTracer(trace=custom)
        d = tracer.get_trace_dict()
        assert "tenantId" in d
        assert "chatAgentId" in d
        assert "contextType" in d


class TestEdgeCases:
    """Tests for edge cases."""

    def test_end_without_start_is_no_op(self) -> None:
        tracer = UnifiedUILangchainTracer()
        unknown_id = _uuid()
        tracer.on_llm_end(
            response=_mock_llm_result("output"),
            run_id=unknown_id,
        )
        assert len(tracer.get_trace().nodes) == 0

    def test_error_without_start_is_no_op(self) -> None:
        tracer = UnifiedUILangchainTracer()
        tracer.on_tool_error(error=Exception("fail"), run_id=_uuid())
        assert len(tracer.get_trace().nodes) == 0

    def test_on_text_logs_to_parent(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"id": ["langchain", "chains", "Chain"]},
            inputs={},
            run_id=run_id,
        )
        tracer.on_text("Some debug info", run_id=_uuid(), parent_run_id=run_id)
        assert "Some debug info" in tracer.get_trace().nodes[0].logs

    def test_serialized_without_id_uses_name(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={"name": "MyCustomChain"},
            inputs={},
            run_id=run_id,
        )
        assert tracer.get_trace().nodes[0].name == "MyCustomChain"

    def test_serialized_empty_uses_fallback(self) -> None:
        tracer = UnifiedUILangchainTracer()
        run_id = _uuid()
        tracer.on_chain_start(
            serialized={},
            inputs={},
            run_id=run_id,
        )
        assert tracer.get_trace().nodes[0].name == "Chain"


def _mock_llm_result(text: str) -> Any:
    from unittest.mock import MagicMock

    mock = MagicMock()
    gen = MagicMock()
    gen.text = text
    mock.generations = [[gen]]
    mock.llm_output = None
    return mock
