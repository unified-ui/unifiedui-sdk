"""Tests for multi-agent orchestrator."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.agents.config import MultiAgentConfig, ReActAgentConfig
from unifiedui_sdk.agents.multi.orchestrator import run_multi_agent
from unifiedui_sdk.streaming.models import StreamMessage, StreamMessageType
from unifiedui_sdk.streaming.writer import StreamWriter


async def _collect(gen):
    """Drain an async generator into a list."""
    return [msg async for msg in gen]


def _make_plan():
    """Create an ExecutionPlan for testing."""
    from unifiedui_sdk.agents.multi.planner import (
        ExecutionPlan,
        ExecutionStep,
        SubAgentTask,
    )

    return ExecutionPlan(
        goal="Test goal",
        reasoning="Test reasoning",
        steps=[
            ExecutionStep(
                step_number=1,
                tasks=[
                    SubAgentTask(
                        id="t1",
                        name="Agent1",
                        description="Do task 1",
                        instructions="Instructions 1",
                        required_tool_names=["search"],
                    ),
                ],
            ),
        ],
    )


class TestRunMultiAgentLifecycle:
    """Tests for multi-agent pipeline lifecycle."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        config = ReActAgentConfig(
            system_prompt="test",
            multi_agent_enabled=True,
            multi_agent=MultiAgentConfig(max_sub_agents=3),
        )
        llm = MagicMock()
        plan = _make_plan()

        exec_msgs = [
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_START,
                config={"sub_agent_id": "t1", "sub_agent_name": "Agent1"},
            ),
            StreamMessage(
                type=StreamMessageType.SUB_AGENT_END,
                config={"sub_agent_id": "t1", "status": "success"},
            ),
        ]

        synth_msgs = [
            StreamMessage(type=StreamMessageType.SYNTHESIS_START),
            StreamMessage(type=StreamMessageType.SYNTHESIS_STREAM, content="result"),
        ]

        async def mock_gen_plan(**_kw):
            return plan

        async def mock_execute(*_a, **_kw):
            for m in exec_msgs:
                yield m

        async def mock_synth(*_a, **_kw):
            for m in synth_msgs:
                yield m

        with (
            patch("unifiedui_sdk.agents.multi.orchestrator.generate_plan", side_effect=mock_gen_plan),
            patch("unifiedui_sdk.agents.multi.orchestrator.execute_plan", side_effect=mock_execute),
            patch("unifiedui_sdk.agents.multi.orchestrator.synthesize", side_effect=mock_synth),
        ):
            msgs = await _collect(
                run_multi_agent(llm=llm, tools=[], config=config, message="complex task")
            )

        types = [m.type for m in msgs]
        assert types[0] == StreamMessageType.STREAM_START
        assert StreamMessageType.PLAN_START in types
        assert StreamMessageType.PLAN_STREAM in types
        assert StreamMessageType.PLAN_COMPLETE in types
        assert StreamMessageType.SUB_AGENT_START in types
        assert StreamMessageType.SYNTHESIS_START in types
        assert types[-1] == StreamMessageType.STREAM_END

    @pytest.mark.asyncio
    async def test_with_history(self) -> None:
        config = ReActAgentConfig(
            multi_agent_enabled=True,
            multi_agent=MultiAgentConfig(),
        )
        llm = MagicMock()
        plan = _make_plan()

        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "system", "content": "sys"},
            {"role": "other", "content": "x"},
        ]

        async def mock_gen_plan(**_kw):
            return plan

        async def mock_execute(*_a, **_kw):
            return
            yield

        async def mock_synth(*_a, **_kw):
            return
            yield

        with (
            patch("unifiedui_sdk.agents.multi.orchestrator.generate_plan", side_effect=mock_gen_plan),
            patch("unifiedui_sdk.agents.multi.orchestrator.execute_plan", side_effect=mock_execute),
            patch("unifiedui_sdk.agents.multi.orchestrator.synthesize", side_effect=mock_synth),
        ):
            msgs = await _collect(
                run_multi_agent(
                    llm=llm, tools=[], config=config, message="test", history=history
                )
            )

        assert msgs[0].type == StreamMessageType.STREAM_START
        assert msgs[-1].type == StreamMessageType.STREAM_END

    @pytest.mark.asyncio
    async def test_custom_writer(self) -> None:
        config = ReActAgentConfig(
            multi_agent_enabled=True,
            multi_agent=MultiAgentConfig(),
        )
        llm = MagicMock()
        plan = _make_plan()
        writer = StreamWriter()

        async def mock_gen_plan(**_kw):
            return plan

        async def mock_execute(*_a, **_kw):
            return
            yield

        async def mock_synth(*_a, **_kw):
            return
            yield

        with (
            patch("unifiedui_sdk.agents.multi.orchestrator.generate_plan", side_effect=mock_gen_plan),
            patch("unifiedui_sdk.agents.multi.orchestrator.execute_plan", side_effect=mock_execute),
            patch("unifiedui_sdk.agents.multi.orchestrator.synthesize", side_effect=mock_synth),
        ):
            msgs = await _collect(
                run_multi_agent(
                    llm=llm, tools=[], config=config, message="test", writer=writer
                )
            )

        assert msgs[0].type == StreamMessageType.STREAM_START
