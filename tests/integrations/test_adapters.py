"""Tests for LangChain and LangGraph stream adapters."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.integrations.langchain.adapter import LangchainStreamAdapter
from unifiedui_sdk.integrations.langgraph.adapter import LanggraphStreamAdapter
from unifiedui_sdk.streaming.models import StreamMessageType


async def _mock_astream_events(
    events: list[dict[str, Any]],
) -> Any:
    """Create an async generator from a list of events."""
    for event in events:
        yield event


def _make_chunk(content: str = "", reasoning: str = "") -> MagicMock:
    """Create a mock LLM chunk."""
    chunk = MagicMock()
    chunk.content = content
    additional = {}
    if reasoning:
        additional["reasoning_content"] = reasoning
    chunk.additional_kwargs = additional
    return chunk


@pytest.fixture
def sample_events() -> list[dict[str, Any]]:
    """Return a sequence of events simulating an agent run with tool use."""
    return [
        {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {"chunk": _make_chunk(reasoning="Let me think...")},
            "run_id": "run-1",
        },
        {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {"chunk": _make_chunk(content="I'll check ")},
            "run_id": "run-1",
        },
        {
            "event": "on_tool_start",
            "name": "get_weather",
            "data": {"input": {"city": "Berlin"}},
            "run_id": "tool-1",
        },
        {
            "event": "on_tool_end",
            "name": "get_weather",
            "data": {"output": "Sunny, 20°C"},
            "run_id": "tool-1",
        },
        {
            "event": "on_chat_model_stream",
            "name": "ChatOpenAI",
            "data": {"chunk": _make_chunk(content="The weather is sunny!")},
            "run_id": "run-2",
        },
    ]


class TestLangchainStreamAdapter:
    """Tests for LangchainStreamAdapter."""

    @pytest.mark.asyncio
    async def test_stream_produces_correct_event_sequence(self, sample_events: list[dict[str, Any]]) -> None:
        mock_agent = MagicMock()
        mock_agent.astream_events = lambda *args, **kwargs: _mock_astream_events(sample_events)

        adapter = LangchainStreamAdapter(agent=mock_agent)
        messages: list[Any] = []
        async for msg in adapter.stream("What's the weather?"):
            messages.append(msg)

        types = [m.type for m in messages]

        assert types[0] == StreamMessageType.STREAM_START
        assert StreamMessageType.REASONING_START in types
        assert StreamMessageType.REASONING_STREAM in types
        assert StreamMessageType.REASONING_END in types
        assert StreamMessageType.TEXT_STREAM in types
        assert StreamMessageType.TOOL_CALL_START in types
        assert StreamMessageType.TOOL_CALL_END in types
        assert StreamMessageType.STREAM_END in types

    @pytest.mark.asyncio
    async def test_stream_tool_call_has_correct_data(self, sample_events: list[dict[str, Any]]) -> None:
        mock_agent = MagicMock()
        mock_agent.astream_events = lambda *args, **kwargs: _mock_astream_events(sample_events)

        adapter = LangchainStreamAdapter(agent=mock_agent)
        messages: list[Any] = []
        async for msg in adapter.stream("test"):
            messages.append(msg)

        tool_start_msgs = [m for m in messages if m.type == StreamMessageType.TOOL_CALL_START]
        assert len(tool_start_msgs) == 1
        assert tool_start_msgs[0].config["tool_name"] == "get_weather"
        assert tool_start_msgs[0].config["tool_arguments"] == {"city": "Berlin"}

        tool_end_msgs = [m for m in messages if m.type == StreamMessageType.TOOL_CALL_END]
        assert len(tool_end_msgs) == 1
        assert tool_end_msgs[0].config["tool_result"] == "Sunny, 20°C"
        assert tool_end_msgs[0].config["tool_status"] == "success"

    @pytest.mark.asyncio
    async def test_stream_text_content(self, sample_events: list[dict[str, Any]]) -> None:
        mock_agent = MagicMock()
        mock_agent.astream_events = lambda *args, **kwargs: _mock_astream_events(sample_events)

        adapter = LangchainStreamAdapter(agent=mock_agent)
        messages: list[Any] = []
        async for msg in adapter.stream("test"):
            messages.append(msg)

        text_msgs = [m for m in messages if m.type == StreamMessageType.TEXT_STREAM]
        assert len(text_msgs) == 2
        assert text_msgs[0].content == "I'll check "
        assert text_msgs[1].content == "The weather is sunny!"


class TestLanggraphStreamAdapter:
    """Tests for LanggraphStreamAdapter."""

    @pytest.mark.asyncio
    async def test_stream_produces_correct_event_sequence(self, sample_events: list[dict[str, Any]]) -> None:
        mock_graph = MagicMock()
        mock_graph.astream_events = lambda *args, **kwargs: _mock_astream_events(sample_events)

        adapter = LanggraphStreamAdapter(graph=mock_graph)

        messages: list[Any] = []
        async for msg in adapter.stream("What's the weather?"):
            messages.append(msg)

        types = [m.type for m in messages]

        assert types[0] == StreamMessageType.STREAM_START
        assert StreamMessageType.TEXT_STREAM in types
        assert StreamMessageType.TOOL_CALL_START in types
        assert StreamMessageType.TOOL_CALL_END in types
        assert StreamMessageType.STREAM_END in types

    @pytest.mark.asyncio
    async def test_filters_internal_nodes(self) -> None:
        events = [
            {
                "event": "on_chain_start",
                "name": "__start__",
                "data": {},
                "run_id": "r1",
            },
            {
                "event": "on_chat_model_stream",
                "name": "ChatOpenAI",
                "data": {"chunk": _make_chunk(content="Hello!")},
                "run_id": "r2",
            },
            {
                "event": "on_chain_end",
                "name": "__end__",
                "data": {},
                "run_id": "r3",
            },
        ]

        mock_graph = MagicMock()
        mock_graph.astream_events = lambda *args, **kwargs: _mock_astream_events(events)

        adapter = LanggraphStreamAdapter(graph=mock_graph)

        messages: list[Any] = []
        async for msg in adapter.stream("test"):
            messages.append(msg)

        types = [m.type for m in messages]
        assert StreamMessageType.STREAM_START in types
        assert StreamMessageType.TEXT_STREAM in types
        assert StreamMessageType.STREAM_END in types

    @pytest.mark.asyncio
    async def test_tool_error_handling(self) -> None:
        events = [
            {
                "event": "on_tool_start",
                "name": "broken_tool",
                "data": {"input": {"q": "test"}},
                "run_id": "t1",
            },
            {
                "event": "on_tool_error",
                "name": "broken_tool",
                "data": {"error": "Connection failed"},
                "run_id": "t1",
            },
        ]

        mock_graph = MagicMock()
        mock_graph.astream_events = lambda *args, **kwargs: _mock_astream_events(events)

        adapter = LanggraphStreamAdapter(graph=mock_graph)

        messages: list[Any] = []
        async for msg in adapter.stream("test"):
            messages.append(msg)

        tool_end_msgs = [m for m in messages if m.type == StreamMessageType.TOOL_CALL_END]
        assert len(tool_end_msgs) == 1
        assert tool_end_msgs[0].config["tool_status"] == "error"
        assert tool_end_msgs[0].config["tool_error"] == "Connection failed"
