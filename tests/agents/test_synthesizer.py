"""Tests for multi-agent synthesizer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.agents.multi.planner import (
    ExecutionPlan,
    ExecutionStep,
    SubAgentTask,
)
from unifiedui_sdk.agents.multi.synthesizer import synthesize
from unifiedui_sdk.streaming.models import StreamMessageType
from unifiedui_sdk.streaming.writer import StreamWriter


async def _collect(gen):
    """Drain an async generator into a list."""
    return [msg async for msg in gen]


def _make_plan_with_results():
    """Create a plan + step_results tuple for testing."""
    plan = ExecutionPlan(
        goal="Compare cities",
        reasoning="Need weather data",
        steps=[
            ExecutionStep(
                step_number=1,
                tasks=[
                    SubAgentTask(
                        id="t1",
                        name="WeatherAgent",
                        description="Get Berlin weather",
                        instructions="Get weather for Berlin",
                    ),
                    SubAgentTask(
                        id="t2",
                        name="NewsAgent",
                        description="Get news",
                        instructions="Get latest news",
                    ),
                ],
            ),
        ],
    )
    step_results = {
        "t1": "Berlin: 12C, cloudy",
        "t2": "Latest headlines...",
    }
    return plan, step_results


class TestSynthesize:
    """Tests for the synthesize function."""

    @pytest.mark.asyncio
    async def test_yields_synthesis_start(self) -> None:
        plan, step_results = _make_plan_with_results()
        llm = MagicMock()
        writer = StreamWriter()

        async def _astream(_msgs):
            chunk = MagicMock()
            chunk.content = "Final answer"
            yield chunk

        llm.astream = _astream

        msgs = await _collect(
            synthesize(
                llm=llm,
                plan=plan,
                step_results=step_results,
                user_message="Compare cities",
                writer=writer,
            )
        )

        types = [m.type for m in msgs]
        assert types[0] == StreamMessageType.SYNTHESIS_START
        assert StreamMessageType.SYNTHESIS_STREAM in types

    @pytest.mark.asyncio
    async def test_streams_multiple_chunks(self) -> None:
        plan, step_results = _make_plan_with_results()
        llm = MagicMock()
        writer = StreamWriter()

        async def _astream(_msgs):
            for text in ["Part 1", " Part 2", " Part 3"]:
                chunk = MagicMock()
                chunk.content = text
                yield chunk

        llm.astream = _astream

        msgs = await _collect(
            synthesize(
                llm=llm,
                plan=plan,
                step_results=step_results,
                user_message="test",
                writer=writer,
            )
        )

        stream_msgs = [m for m in msgs if m.type == StreamMessageType.SYNTHESIS_STREAM]
        assert len(stream_msgs) == 3
        assert stream_msgs[0].content == "Part 1"

    @pytest.mark.asyncio
    async def test_skips_empty_chunks(self) -> None:
        plan, step_results = _make_plan_with_results()
        llm = MagicMock()
        writer = StreamWriter()

        async def _astream(_msgs):
            chunk_empty = MagicMock()
            chunk_empty.content = ""
            yield chunk_empty

            chunk_full = MagicMock()
            chunk_full.content = "content"
            yield chunk_full

        llm.astream = _astream

        msgs = await _collect(
            synthesize(
                llm=llm,
                plan=plan,
                step_results=step_results,
                user_message="test",
                writer=writer,
            )
        )

        stream_msgs = [m for m in msgs if m.type == StreamMessageType.SYNTHESIS_STREAM]
        assert len(stream_msgs) == 1
        assert stream_msgs[0].content == "content"

    @pytest.mark.asyncio
    async def test_missing_result_shows_no_result(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(id="missing_t", name="A", description="d", instructions="i"),
                    ],
                ),
            ],
        )
        llm = MagicMock()
        writer = StreamWriter()

        async def _astream(_msgs):
            chunk = MagicMock()
            chunk.content = "done"
            yield chunk

        llm.astream = _astream

        msgs = await _collect(
            synthesize(
                llm=llm, plan=plan, step_results={}, user_message="test", writer=writer
            )
        )

        assert any(m.type == StreamMessageType.SYNTHESIS_STREAM for m in msgs)
