"""Tests for base tracer module internals."""

from __future__ import annotations

from uuid import UUID, uuid4

from unifiedui_sdk.tracing.base import BaseTracer, _extract_name
from unifiedui_sdk.tracing.models import (
    NodeStatus,
    Trace,
)


def _uuid() -> UUID:
    return uuid4()


class TestExtractName:
    """Tests for the _extract_name helper."""

    def test_extracts_last_id_element(self) -> None:
        assert _extract_name({"id": ["langchain", "llms", "AzureChatOpenAI"]}, "LLM") == "AzureChatOpenAI"

    def test_extracts_name_field(self) -> None:
        assert _extract_name({"name": "MyChain"}, "Chain") == "MyChain"

    def test_id_takes_precedence_over_name(self) -> None:
        assert _extract_name({"id": ["a", "B"], "name": "C"}, "D") == "B"

    def test_none_returns_fallback(self) -> None:
        assert _extract_name(None, "Fallback") == "Fallback"

    def test_empty_dict_returns_fallback(self) -> None:
        assert _extract_name({}, "Fallback") == "Fallback"

    def test_empty_id_list_uses_name(self) -> None:
        assert _extract_name({"id": [], "name": "X"}, "F") == "X"

    def test_empty_id_list_no_name_uses_fallback(self) -> None:
        assert _extract_name({"id": []}, "F") == "F"


class TestResolveNameDefault:
    """Tests for the default _resolve_name implementation in BaseTracer."""

    def test_kwargs_name_takes_priority(self) -> None:
        tracer = BaseTracer()
        result = tracer._resolve_name(
            {"id": ["a", "SerializedName"]},
            "Fallback",
            name="KwargsName",
        )
        assert result == "KwargsName"

    def test_falls_through_to_serialized(self) -> None:
        tracer = BaseTracer()
        result = tracer._resolve_name(
            {"id": ["langchain", "OpenAI"]},
            "Fallback",
        )
        assert result == "OpenAI"

    def test_none_serialized_returns_fallback(self) -> None:
        tracer = BaseTracer()
        result = tracer._resolve_name(None, "MyFallback")
        assert result == "MyFallback"

    def test_none_name_kwarg_uses_serialized(self) -> None:
        tracer = BaseTracer()
        result = tracer._resolve_name(
            {"name": "SerName"},
            "Fallback",
            name=None,
        )
        assert result == "SerName"

    def test_empty_string_name_uses_serialized(self) -> None:
        tracer = BaseTracer()
        result = tracer._resolve_name(
            {"id": ["a", "Extracted"]},
            "Fallback",
            name="",
        )
        assert result == "Extracted"


class TestShouldTraceNodeDefault:
    """Tests for the default _should_trace_node (always True)."""

    def test_default_always_returns_true(self) -> None:
        tracer = BaseTracer()
        assert tracer._should_trace_node("anything") is True
        assert tracer._should_trace_node("__start__") is True
        assert tracer._should_trace_node("__end__") is True
        assert tracer._should_trace_node("") is True


class TestBaseTracerIsInstantiable:
    """Verify BaseTracer can be used directly (not abstract)."""

    def test_direct_instantiation(self) -> None:
        tracer = BaseTracer()
        assert isinstance(tracer.get_trace(), Trace)
        assert tracer.get_trace().nodes == []

    def test_callbacks_work_on_base(self) -> None:
        tracer = BaseTracer()
        run_id = _uuid()
        tracer.on_chain_start(serialized={}, inputs={"x": 1}, run_id=run_id, name="TestChain")
        tracer.on_chain_end(outputs={"y": 2}, run_id=run_id)

        node = tracer.get_trace().nodes[0]
        assert node.name == "TestChain"
        assert node.status == NodeStatus.COMPLETED

    def test_get_trace_dict_on_base(self) -> None:
        tracer = BaseTracer()
        run_id = _uuid()
        tracer.on_tool_start(serialized={"name": "calc"}, input_str="2+2", run_id=run_id)
        tracer.on_tool_end(output="4", run_id=run_id)

        d = tracer.get_trace_dict()
        assert isinstance(d, dict)
        assert d["nodes"][0]["name"] == "calc"
        assert d["nodes"][0]["type"] == "tool"
