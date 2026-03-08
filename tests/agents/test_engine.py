"""Tests for ReActAgentEngine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.agents.config import MultiAgentConfig, ReActAgentConfig
from unifiedui_sdk.agents.engine import ReActAgentEngine
from unifiedui_sdk.streaming.models import StreamMessage, StreamMessageType
from unifiedui_sdk.tracing.react_agent import ReActAgentTracer


def _make_stream_messages(types: list[StreamMessageType]) -> list[StreamMessage]:
    """Create a list of StreamMessage objects with given types."""
    msgs = []
    for t in types:
        content = "token" if t in (StreamMessageType.TEXT_STREAM, StreamMessageType.SYNTHESIS_STREAM) else ""
        msgs.append(StreamMessage(type=t, content=content))
    return msgs


async def _mock_gen(msgs: list[StreamMessage]):
    """Create a mock async generator yielding given messages."""
    for msg in msgs:
        yield msg


class TestReActAgentEngineProperties:
    """Tests for ReActAgentEngine properties."""

    def test_config_property(self) -> None:
        config = ReActAgentConfig(system_prompt="test")
        llm = MagicMock()
        engine = ReActAgentEngine(config=config, llm=llm, tools=[])
        assert engine.config is config

    def test_is_multi_agent_false(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=False)
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        assert engine.is_multi_agent is False

    def test_is_multi_agent_true(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=True)
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        assert engine.is_multi_agent is True


class TestReActAgentEngineSingleAgent:
    """Tests for single-agent mode."""

    @pytest.mark.asyncio
    async def test_invoke_stream_single_agent(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=False)
        llm = MagicMock()

        expected_msgs = _make_stream_messages(
            [
                StreamMessageType.STREAM_START,
                StreamMessageType.TEXT_STREAM,
                StreamMessageType.STREAM_END,
            ]
        )

        with patch.object(
            ReActAgentEngine,
            "_run_single_agent",
            return_value=_mock_gen(expected_msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[])
            collected: list[StreamMessage] = []
            async for msg in engine.invoke_stream("Hello"):
                collected.append(msg)

        types = [m.type for m in collected]
        assert StreamMessageType.STREAM_START in types
        assert StreamMessageType.TEXT_STREAM in types
        assert StreamMessageType.STREAM_END in types

    @pytest.mark.asyncio
    async def test_invoke_single_agent(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=False)
        llm = MagicMock()

        expected_msgs = _make_stream_messages(
            [
                StreamMessageType.STREAM_START,
                StreamMessageType.TEXT_STREAM,
                StreamMessageType.TEXT_STREAM,
                StreamMessageType.STREAM_END,
            ]
        )

        with patch.object(
            ReActAgentEngine,
            "_run_single_agent",
            return_value=_mock_gen(expected_msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[])
            result = await engine.invoke("Hello")

        assert result == "tokentoken"


class TestReActAgentEngineMultiAgent:
    """Tests for multi-agent mode."""

    @pytest.mark.asyncio
    async def test_invoke_stream_multi_agent(self) -> None:
        config = ReActAgentConfig(
            multi_agent_enabled=True,
            multi_agent=MultiAgentConfig(max_sub_agents=3),
        )
        llm = MagicMock()

        expected_msgs = [
            StreamMessage(type=StreamMessageType.STREAM_START),
            StreamMessage(type=StreamMessageType.PLAN_START),
            StreamMessage(type=StreamMessageType.PLAN_COMPLETE, config={"plan": {"goal": "test"}}),
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_START,
                config={"sub_agent_id": "sa_1", "sub_agent_name": "A", "step_number": 1, "tools": []},
            ),
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_END,
                config={"sub_agent_id": "sa_1", "status": "success", "result_summary": "ok"},
            ),
            StreamMessage(type=StreamMessageType.SYNTHESIS_START),
            StreamMessage(type=StreamMessageType.SYNTHESIS_STREAM, content="token"),
            StreamMessage(type=StreamMessageType.STREAM_END),
        ]

        with patch.object(
            ReActAgentEngine,
            "_run_multi_agent",
            return_value=_mock_gen(expected_msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[])
            collected: list[StreamMessage] = []
            async for msg in engine.invoke_stream("Complex task"):
                collected.append(msg)

        types = [m.type for m in collected]
        assert StreamMessageType.PLAN_START in types
        assert StreamMessageType.SYNTHESIS_STREAM in types

    @pytest.mark.asyncio
    async def test_invoke_multi_agent_returns_synthesis(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=True)
        llm = MagicMock()

        msgs = [
            StreamMessage(type=StreamMessageType.STREAM_START),
            StreamMessage(type=StreamMessageType.TEXT_STREAM, content="ignored"),
            StreamMessage(type=StreamMessageType.SYNTHESIS_STREAM, content="final "),
            StreamMessage(type=StreamMessageType.SYNTHESIS_STREAM, content="answer"),
            StreamMessage(type=StreamMessageType.STREAM_END),
        ]

        with patch.object(
            ReActAgentEngine,
            "_run_multi_agent",
            return_value=_mock_gen(msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[])
            result = await engine.invoke("task")

        assert result == "final answer"


class TestReActAgentEngineTracer:
    """Tests for tracer integration."""

    @pytest.mark.asyncio
    async def test_tracer_receives_events(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=True)
        tracer = ReActAgentTracer()
        llm = MagicMock()

        msgs = [
            StreamMessage(type=StreamMessageType.STREAM_START),
            StreamMessage(type=StreamMessageType.PLAN_START),
            StreamMessage(
                type=StreamMessageType.PLAN_COMPLETE,
                config={"plan": {"goal": "G", "steps": []}},
            ),
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_START,
                config={"sub_agent_id": "sa_1", "sub_agent_name": "A", "step_number": 1, "tools": []},
            ),
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_END,
                config={"sub_agent_id": "sa_1", "status": "success", "result_summary": "ok"},
            ),
            StreamMessage(type=StreamMessageType.SYNTHESIS_START),
            StreamMessage(type=StreamMessageType.STREAM_END),
        ]

        with patch.object(
            ReActAgentEngine,
            "_run_multi_agent",
            return_value=_mock_gen(msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[], tracer=tracer)
            collected: list[StreamMessage] = []
            async for msg in engine.invoke_stream("task"):
                collected.append(msg)

        trace = tracer.get_trace()
        node_names = [n.name for n in trace.nodes]
        assert "Planner" in node_names
        assert "SubAgent: A" in node_names
        assert "Synthesizer" in node_names

    @pytest.mark.asyncio
    async def test_trace_message_appended_at_end(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=False)
        tracer = ReActAgentTracer()
        llm = MagicMock()

        msgs = [
            StreamMessage(type=StreamMessageType.STREAM_START),
            StreamMessage(type=StreamMessageType.STREAM_END),
        ]

        with patch.object(
            ReActAgentEngine,
            "_run_single_agent",
            return_value=_mock_gen(msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[], tracer=tracer)
            collected: list[StreamMessage] = []
            async for msg in engine.invoke_stream("hello"):
                collected.append(msg)

        last_msg = collected[-1]
        assert last_msg.type == StreamMessageType.TRACE

    @pytest.mark.asyncio
    async def test_no_tracer_no_trace_message(self) -> None:
        config = ReActAgentConfig(multi_agent_enabled=False)
        llm = MagicMock()

        msgs = [
            StreamMessage(type=StreamMessageType.STREAM_START),
            StreamMessage(type=StreamMessageType.STREAM_END),
        ]

        with patch.object(
            ReActAgentEngine,
            "_run_single_agent",
            return_value=_mock_gen(msgs),
        ):
            engine = ReActAgentEngine(config=config, llm=llm, tools=[])
            collected: list[StreamMessage] = []
            async for msg in engine.invoke_stream("hello"):
                collected.append(msg)

        types = [m.type for m in collected]
        assert StreamMessageType.TRACE not in types


class TestForwardToTracer:
    """Tests for _forward_to_tracer method."""

    def test_plan_start_forwarded(self) -> None:
        tracer = ReActAgentTracer()
        config = ReActAgentConfig()
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        msg = StreamMessage(type=StreamMessageType.PLAN_START)
        engine._forward_to_tracer(tracer, msg)
        trace = tracer.get_trace()
        assert any(n.name == "Planner" for n in trace.nodes)

    def test_plan_complete_forwarded(self) -> None:
        tracer = ReActAgentTracer()
        config = ReActAgentConfig()
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        engine._forward_to_tracer(tracer, StreamMessage(type=StreamMessageType.PLAN_START))
        engine._forward_to_tracer(
            tracer,
            StreamMessage(
                type=StreamMessageType.PLAN_COMPLETE,
                config={"plan": {"goal": "test", "steps": []}},
            ),
        )
        trace = tracer.get_trace()
        planner = trace.nodes[0]
        assert planner.metadata.get("plan_goal") == "test"

    def test_tool_call_with_sub_agent_forwarded(self) -> None:
        tracer = ReActAgentTracer()
        config = ReActAgentConfig()
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])

        engine._forward_to_tracer(
            tracer,
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_START,
                config={"sub_agent_id": "sa_1", "sub_agent_name": "A", "step_number": 1, "tools": ["t1"]},
            ),
        )
        engine._forward_to_tracer(
            tracer,
            StreamMessage(
                type=StreamMessageType.TOOL_CALL_START,
                config={"sub_agent_id": "sa_1", "tool_call_id": "tc_1", "tool_name": "t1", "tool_arguments": {}},
            ),
        )

        trace = tracer.get_trace()
        sa_node = trace.nodes[0]
        assert len(sa_node.nodes) == 1
        assert sa_node.nodes[0].name == "t1"

    def test_tool_call_without_sub_agent_not_forwarded(self) -> None:
        tracer = ReActAgentTracer()
        config = ReActAgentConfig()
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        engine._forward_to_tracer(
            tracer,
            StreamMessage(
                type=StreamMessageType.TOOL_CALL_START,
                config={"tool_call_id": "tc_1", "tool_name": "t1", "tool_arguments": {}},
            ),
        )
        trace = tracer.get_trace()
        assert len(trace.nodes) == 0

    def test_synthesis_start_forwarded(self) -> None:
        tracer = ReActAgentTracer()
        config = ReActAgentConfig()
        engine = ReActAgentEngine(config=config, llm=MagicMock(), tools=[])
        engine._forward_to_tracer(tracer, StreamMessage(type=StreamMessageType.SYNTHESIS_START))
        trace = tracer.get_trace()
        assert any(n.name == "Synthesizer" for n in trace.nodes)
