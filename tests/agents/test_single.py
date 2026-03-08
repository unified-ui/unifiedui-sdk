"""Tests for single-agent executor."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.agents.config import ReActAgentConfig
from unifiedui_sdk.agents.single import run_single_agent
from unifiedui_sdk.streaming.models import StreamMessageType
from unifiedui_sdk.streaming.writer import StreamWriter


def _setup_langchain_mock(mock_graph: MagicMock):
    """Install a mock langchain.agents module with a create_agent that returns mock_graph."""
    mock_agents_module = MagicMock()
    mock_agents_module.create_agent = MagicMock(return_value=mock_graph)
    return patch.dict(
        sys.modules,
        {
            "langchain": MagicMock(),
            "langchain.agents": mock_agents_module,
        },
    )


def _chunk(content: str = "", reasoning: str = "") -> MagicMock:
    """Create a mock AIMessageChunk."""
    chunk = MagicMock()
    chunk.content = content
    if reasoning:
        chunk.additional_kwargs = {"reasoning_content": reasoning}
    else:
        chunk.additional_kwargs = {}
    return chunk


def _event(kind: str, **extra: object) -> dict[str, object]:
    """Build a mock LangGraph stream event."""
    ev: dict[str, object] = {"event": kind}
    ev.update(extra)
    return ev


async def _collect(gen):
    """Drain an async generator into a list."""
    return [msg async for msg in gen]


class TestRunSingleAgentBasic:
    """Basic streaming lifecycle tests."""

    @pytest.mark.asyncio
    async def test_yields_start_and_end(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()

        mock_graph = MagicMock()

        async def _no_events(*_a, **_kw):
            return
            yield  # make it an async generator

        mock_graph.astream_events = _no_events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="hi"))

        types = [m.type for m in msgs]
        assert types[0] == StreamMessageType.STREAM_START
        assert types[-1] == StreamMessageType.STREAM_END

    @pytest.mark.asyncio
    async def test_text_stream(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(content="Hello")},
            )
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(content=" world")},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="hi"))

        text_msgs = [m for m in msgs if m.type == StreamMessageType.TEXT_STREAM]
        assert len(text_msgs) == 2
        assert text_msgs[0].content == "Hello"
        assert text_msgs[1].content == " world"


class TestRunSingleAgentReasoning:
    """Reasoning events tests."""

    @pytest.mark.asyncio
    async def test_reasoning_stream(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(reasoning="thinking...")},
            )
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(reasoning="more thought")},
            )
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(content="answer")},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="hi"))

        types = [m.type for m in msgs]
        assert StreamMessageType.REASONING_START in types
        assert StreamMessageType.REASONING_STREAM in types
        assert StreamMessageType.REASONING_END in types
        assert StreamMessageType.TEXT_STREAM in types

    @pytest.mark.asyncio
    async def test_reasoning_end_emitted_at_stream_end(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_chat_model_stream",
                data={"chunk": _chunk(reasoning="thinking...")},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="hi"))

        types = [m.type for m in msgs]
        assert types[-2] == StreamMessageType.REASONING_END
        assert types[-1] == StreamMessageType.STREAM_END


class TestRunSingleAgentTools:
    """Tool call event tests."""

    @pytest.mark.asyncio
    async def test_tool_call_lifecycle(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_tool_start",
                run_id="run_1",
                name="calculator",
                data={"input": {"expr": "1+1"}},
            )
            yield _event(
                "on_tool_end",
                run_id="run_1",
                name="calculator",
                data={"output": "2"},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="calc"))

        types = [m.type for m in msgs]
        assert StreamMessageType.TOOL_CALL_START in types
        assert StreamMessageType.TOOL_CALL_END in types

        start_msg = next(m for m in msgs if m.type == StreamMessageType.TOOL_CALL_START)
        assert start_msg.config["tool_name"] == "calculator"

        end_msg = next(m for m in msgs if m.type == StreamMessageType.TOOL_CALL_END)
        assert end_msg.config["tool_status"] == "success"
        assert end_msg.config["tool_result"] == "2"

    @pytest.mark.asyncio
    async def test_tool_error(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_tool_start",
                run_id="run_2",
                name="broken",
                data={"input": "x"},
            )
            yield _event(
                "on_tool_error",
                run_id="run_2",
                name="broken",
                data={"error": "boom"},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="err"))

        end_msg = next(m for m in msgs if m.type == StreamMessageType.TOOL_CALL_END)
        assert end_msg.config["tool_status"] == "error"
        assert end_msg.config["tool_error"] == "boom"

    @pytest.mark.asyncio
    async def test_tool_string_input(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield _event(
                "on_tool_start",
                run_id="r3",
                name="search",
                data={"input": "raw-string"},
            )
            yield _event(
                "on_tool_end",
                run_id="r3",
                name="search",
                data={"output": 42},
            )

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="s"))

        start_msg = next(m for m in msgs if m.type == StreamMessageType.TOOL_CALL_START)
        assert start_msg.config["tool_arguments"] == {"input": "raw-string"}


class TestRunSingleAgentHistory:
    """History and writer tests."""

    @pytest.mark.asyncio
    async def test_with_history(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            return
            yield

        mock_graph.astream_events = _events

        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
            {"role": "system", "content": "be helpful"},
            {"role": "other", "content": "ignored"},
        ]

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="test", history=history))

        assert msgs[0].type == StreamMessageType.STREAM_START

    @pytest.mark.asyncio
    async def test_custom_writer(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            return
            yield

        mock_graph.astream_events = _events

        writer = StreamWriter()

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="test", writer=writer))

        assert msgs[0].type == StreamMessageType.STREAM_START

    @pytest.mark.asyncio
    async def test_chunk_without_content(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        mock_graph = MagicMock()

        chunk_no_content = MagicMock()
        chunk_no_content.content = ""
        chunk_no_content.additional_kwargs = {}

        async def _events(*_a, **_kw):
            yield _event("on_chat_model_stream", data={"chunk": chunk_no_content})
            yield _event("on_chat_model_stream", data={"chunk": None})

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(run_single_agent(llm=llm, tools=[], config=config, message="test"))

        text_msgs = [m for m in msgs if m.type == StreamMessageType.TEXT_STREAM]
        assert len(text_msgs) == 0
