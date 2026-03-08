"""Tests for multi-agent executor."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from unifiedui_sdk.agents.multi.executor import execute_plan
from unifiedui_sdk.agents.multi.planner import (
    ExecutionPlan,
    ExecutionStep,
    SubAgentTask,
)
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


async def _collect(gen):
    """Drain an async generator into a list."""
    return [msg async for msg in gen]


def _make_tool(name: str) -> MagicMock:
    """Create a mock BaseTool."""
    tool = MagicMock()
    tool.name = name
    return tool


def _chunk(content: str = "") -> MagicMock:
    """Create a mock AIMessageChunk."""
    c = MagicMock()
    c.content = content
    return c


class TestExecutePlanSingleStep:
    """Tests for executing a single-step plan."""

    @pytest.mark.asyncio
    async def test_single_task_success(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="Agent1",
                            description="do stuff",
                            instructions="inst",
                            required_tool_names=["search"],
                        ),
                    ],
                ),
            ],
        )

        tools = [_make_tool("search")]
        writer = StreamWriter()
        step_results: dict[str, str] = {}

        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": _chunk("result text")},
            }

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=tools,
                    writer=writer,
                    step_results=step_results,
                )
            )

        types = [m.type for m in msgs]
        assert StreamMessageType.SUB_AGENT_START in types
        assert StreamMessageType.SUB_AGENT_STREAM in types
        assert StreamMessageType.SUB_AGENT_END in types
        assert "t1" in step_results

    @pytest.mark.asyncio
    async def test_task_with_tool_events(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="ToolUser",
                            description="use tool",
                            instructions="use it",
                            required_tool_names=["calc"],
                        ),
                    ],
                ),
            ],
        )

        tools = [_make_tool("calc")]
        writer = StreamWriter()
        step_results: dict[str, str] = {}
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield {
                "event": "on_tool_start",
                "run_id": "r1",
                "name": "calc",
                "data": {"input": {"a": "1+1"}},
            }
            yield {
                "event": "on_tool_end",
                "run_id": "r1",
                "name": "calc",
                "data": {"output": "2"},
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": _chunk("answer")},
            }

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=tools,
                    writer=writer,
                    step_results=step_results,
                )
            )

        types = [m.type for m in msgs]
        assert StreamMessageType.TOOL_CALL_START in types
        assert StreamMessageType.TOOL_CALL_END in types

    @pytest.mark.asyncio
    async def test_task_error(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="ErrorAgent",
                            description="will fail",
                            instructions="fail",
                        ),
                    ],
                ),
            ],
        )

        writer = StreamWriter()
        step_results: dict[str, str] = {}
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            msg = "test error"
            raise RuntimeError(msg)
            yield

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=[],
                    writer=writer,
                    step_results=step_results,
                )
            )

        end_msgs = [m for m in msgs if m.type == StreamMessageType.SUB_AGENT_END]
        assert len(end_msgs) == 1
        assert end_msgs[0].config.get("status") == "error"
        assert "t1" in step_results
        assert "Error" in step_results["t1"]


class TestExecutePlanMultiStep:
    """Tests for multi-step plans with dependencies."""

    @pytest.mark.asyncio
    async def test_two_steps_with_dependency(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(id="t1", name="A", description="d", instructions="i"),
                    ],
                ),
                ExecutionStep(
                    step_number=2,
                    tasks=[
                        SubAgentTask(id="t2", name="B", description="d", instructions="i", depends_on=["t1"]),
                    ],
                ),
            ],
        )

        writer = StreamWriter()
        step_results: dict[str, str] = {}
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": _chunk("done")},
            }

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=[],
                    writer=writer,
                    step_results=step_results,
                    security_prompt="be safe",
                )
            )

        assert "t1" in step_results
        assert "t2" in step_results

        start_msgs = [m for m in msgs if m.type == StreamMessageType.SUB_AGENT_START]
        assert len(start_msgs) == 2

    @pytest.mark.asyncio
    async def test_parallel_tasks_in_step(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(id="t1", name="A", description="d", instructions="i"),
                        SubAgentTask(id="t2", name="B", description="d", instructions="i"),
                    ],
                ),
            ],
        )

        writer = StreamWriter()
        step_results: dict[str, str] = {}
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": _chunk("ok")},
            }

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=[],
                    writer=writer,
                    step_results=step_results,
                    max_parallel_per_step=2,
                )
            )

        assert "t1" in step_results
        assert "t2" in step_results

    @pytest.mark.asyncio
    async def test_string_tool_input(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(id="t1", name="A", description="d", instructions="i"),
                    ],
                ),
            ],
        )

        writer = StreamWriter()
        step_results: dict[str, str] = {}
        mock_graph = MagicMock()

        async def _events(*_a, **_kw):
            yield {
                "event": "on_tool_start",
                "run_id": "r1",
                "name": "search",
                "data": {"input": "raw_string_input"},
            }
            yield {
                "event": "on_tool_end",
                "run_id": "r1",
                "name": "search",
                "data": {"output": "found"},
            }

        mock_graph.astream_events = _events

        with _setup_langchain_mock(mock_graph):
            msgs = await _collect(
                execute_plan(
                    plan=plan,
                    llm=MagicMock(),
                    tools=[],
                    writer=writer,
                    step_results=step_results,
                )
            )

        tool_start = [m for m in msgs if m.type == StreamMessageType.TOOL_CALL_START]
        assert len(tool_start) == 1
        assert tool_start[0].config["tool_arguments"] == {"input": "raw_string_input"}
