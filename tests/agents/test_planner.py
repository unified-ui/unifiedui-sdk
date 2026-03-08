"""Tests for planner models and validation."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from unifiedui_sdk.agents.multi.planner import (
    ExecutionPlan,
    ExecutionStep,
    SubAgentTask,
    _validate_plan,
    generate_plan,
)


class TestSubAgentTask:
    """Tests for SubAgentTask model."""

    def test_minimal(self) -> None:
        task = SubAgentTask(
            id="task_1",
            name="Test Agent",
            description="Do something",
            instructions="Just do it",
        )
        assert task.id == "task_1"
        assert task.name == "Test Agent"
        assert task.required_tool_names == []
        assert task.depends_on == []

    def test_with_tools_and_deps(self) -> None:
        task = SubAgentTask(
            id="task_2",
            name="Analyzer",
            description="Analyze data",
            instructions="Analyze it",
            required_tool_names=["search", "calc"],
            depends_on=["task_1"],
        )
        assert task.required_tool_names == ["search", "calc"]
        assert task.depends_on == ["task_1"]


class TestExecutionStep:
    """Tests for ExecutionStep model."""

    def test_basic(self) -> None:
        task = SubAgentTask(id="t1", name="A", description="d", instructions="i")
        step = ExecutionStep(step_number=1, tasks=[task])
        assert step.step_number == 1
        assert len(step.tasks) == 1

    def test_multiple_tasks(self) -> None:
        tasks = [SubAgentTask(id=f"t{i}", name=f"Agent{i}", description="d", instructions="i") for i in range(3)]
        step = ExecutionStep(step_number=2, tasks=tasks)
        assert len(step.tasks) == 3


class TestExecutionPlan:
    """Tests for ExecutionPlan model."""

    def test_basic(self) -> None:
        plan = ExecutionPlan(
            goal="Test goal",
            reasoning="Because",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                )
            ],
        )
        assert plan.goal == "Test goal"
        assert plan.reasoning == "Because"
        assert len(plan.steps) == 1
        assert plan.estimated_complexity == "moderate"

    def test_custom_complexity(self) -> None:
        plan = ExecutionPlan(
            goal="g",
            reasoning="r",
            steps=[],
            estimated_complexity="complex",
        )
        assert plan.estimated_complexity == "complex"

    def test_model_dump(self) -> None:
        plan = ExecutionPlan(
            goal="g",
            reasoning="r",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                ),
            ],
        )
        dumped = plan.model_dump()
        assert dumped["goal"] == "g"
        assert len(dumped["steps"]) == 1
        assert dumped["steps"][0]["tasks"][0]["id"] == "t1"


class TestValidatePlan:
    """Tests for _validate_plan function."""

    @staticmethod
    def _make_tool(name: str) -> MagicMock:
        tool = MagicMock()
        tool.name = name
        return tool

    def test_valid_plan_passes(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="test",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="A",
                            description="d",
                            instructions="i",
                            required_tool_names=["search"],
                        )
                    ],
                ),
                ExecutionStep(
                    step_number=2,
                    tasks=[
                        SubAgentTask(
                            id="t2",
                            name="B",
                            description="d",
                            instructions="i",
                            depends_on=["t1"],
                        )
                    ],
                ),
            ],
        )
        tools = [self._make_tool("search"), self._make_tool("calc")]
        _validate_plan(plan, tools)

    def test_unknown_tool_raises(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="test",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="A",
                            description="d",
                            instructions="i",
                            required_tool_names=["nonexistent_tool"],
                        )
                    ],
                ),
            ],
        )
        tools = [self._make_tool("search")]
        with pytest.raises(ValueError, match="unknown tool"):
            _validate_plan(plan, tools)

    def test_unknown_dependency_raises(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="test",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[
                        SubAgentTask(
                            id="t1",
                            name="A",
                            description="d",
                            instructions="i",
                            depends_on=["nonexistent_task"],
                        )
                    ],
                ),
            ],
        )
        tools: list[MagicMock] = []
        with pytest.raises(ValueError, match="unknown task"):
            _validate_plan(plan, tools)

    def test_no_tools_no_refs_passes(self) -> None:
        plan = ExecutionPlan(
            goal="test",
            reasoning="test",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                ),
            ],
        )
        _validate_plan(plan, [])


class TestGeneratePlan:
    """Tests for generate_plan function."""

    @staticmethod
    def _make_tool(name: str, desc: str = "A tool") -> MagicMock:
        tool = MagicMock()
        tool.name = name
        tool.description = desc
        return tool

    @pytest.mark.asyncio
    async def test_returns_valid_plan(self) -> None:
        plan = ExecutionPlan(
            goal="Test",
            reasoning="Because",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                ),
            ],
        )

        structured_llm = AsyncMock()
        structured_llm.ainvoke = AsyncMock(return_value=plan)

        llm = MagicMock()
        llm.with_structured_output = MagicMock(return_value=structured_llm)

        from langchain_core.messages import HumanMessage

        result = await generate_plan(
            llm=llm,
            tools=[self._make_tool("search")],
            messages=[HumanMessage(content="test")],
        )

        assert result.goal == "Test"
        assert len(result.steps) == 1

    @pytest.mark.asyncio
    async def test_retries_on_none(self) -> None:
        valid_plan = ExecutionPlan(
            goal="OK",
            reasoning="R",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                ),
            ],
        )

        structured_llm = AsyncMock()
        structured_llm.ainvoke = AsyncMock(side_effect=[None, valid_plan])

        llm = MagicMock()
        llm.with_structured_output = MagicMock(return_value=structured_llm)

        from langchain_core.messages import HumanMessage

        result = await generate_plan(
            llm=llm,
            tools=[],
            messages=[HumanMessage(content="test")],
            max_iterations=2,
        )

        assert result.goal == "OK"

    @pytest.mark.asyncio
    async def test_raises_after_max_iterations(self) -> None:
        structured_llm = AsyncMock()
        structured_llm.ainvoke = AsyncMock(return_value=None)

        llm = MagicMock()
        llm.with_structured_output = MagicMock(return_value=structured_llm)

        from langchain_core.messages import HumanMessage

        with pytest.raises(ValueError, match="Failed to generate"):
            await generate_plan(
                llm=llm,
                tools=[],
                messages=[HumanMessage(content="test")],
                max_iterations=2,
            )

    @pytest.mark.asyncio
    async def test_raises_on_exception_after_retries(self) -> None:
        structured_llm = AsyncMock()
        structured_llm.ainvoke = AsyncMock(side_effect=RuntimeError("LLM error"))

        llm = MagicMock()
        llm.with_structured_output = MagicMock(return_value=structured_llm)

        from langchain_core.messages import HumanMessage

        with pytest.raises(RuntimeError, match="LLM error"):
            await generate_plan(
                llm=llm,
                tools=[],
                messages=[HumanMessage(content="test")],
                max_iterations=1,
            )

    @pytest.mark.asyncio
    async def test_with_security_prompt(self) -> None:
        plan = ExecutionPlan(
            goal="Safe",
            reasoning="R",
            steps=[
                ExecutionStep(
                    step_number=1,
                    tasks=[SubAgentTask(id="t1", name="A", description="d", instructions="i")],
                ),
            ],
        )

        structured_llm = AsyncMock()
        structured_llm.ainvoke = AsyncMock(return_value=plan)

        llm = MagicMock()
        llm.with_structured_output = MagicMock(return_value=structured_llm)

        from langchain_core.messages import HumanMessage

        result = await generate_plan(
            llm=llm,
            tools=[self._make_tool("search", "search tool")],
            messages=[HumanMessage(content="test")],
            security_prompt="Be very careful",
        )

        assert result.goal == "Safe"
