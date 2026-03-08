"""Orchestrator — full multi-agent pipeline (plan → execute → synthesize)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from unifiedui_sdk.agents.multi.executor import execute_plan
from unifiedui_sdk.agents.multi.planner import generate_plan
from unifiedui_sdk.agents.multi.synthesizer import synthesize
from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from unifiedui_sdk.agents.config import ReActAgentConfig
    from unifiedui_sdk.streaming.models import StreamMessage


async def run_multi_agent(
    llm: BaseChatModel,
    tools: list[BaseTool],
    config: ReActAgentConfig,
    message: str,
    history: list[dict[str, str]] | None = None,
    *,
    writer: StreamWriter | None = None,
    callbacks: list[Any] | None = None,
) -> AsyncGenerator[StreamMessage]:
    """Execute a multi-agent orchestration pipeline and stream results.

    Pipeline: Plan → Execute (parallel sub-agents) → Synthesize.

    Args:
        llm: LangChain chat model instance.
        tools: List of all available LangChain tools.
        config: Agent configuration with multi-agent settings.
        message: User message to process.
        history: Optional conversation history.
        writer: Optional StreamWriter (creates one if not provided).
        callbacks: Optional LangChain callbacks (tracers, etc.).

    Yields:
        StreamMessage objects for the full multi-agent SSE lifecycle.
    """
    sw = writer or StreamWriter()
    multi_cfg = config.multi_agent

    messages: list[Any] = []
    if history:
        for entry in history:
            role = entry.get("role", "user")
            content = entry.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                from langchain_core.messages import AIMessage

                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
    messages.append(HumanMessage(content=message))

    yield sw.stream_start()

    # --- Planning phase ---
    yield sw.plan_start()
    yield sw.plan_stream("Analyzing the request and creating an execution plan...")

    plan = await generate_plan(
        llm=llm,
        tools=tools,
        messages=messages,
        security_prompt=config.security_prompt or "",
        max_iterations=multi_cfg.max_planning_iterations,
    )

    yield sw.plan_complete(plan.model_dump())

    # --- Execution phase ---
    step_results: dict[str, str] = {}

    async for msg in execute_plan(
        plan=plan,
        llm=llm,
        tools=tools,
        writer=sw,
        step_results=step_results,
        sub_agent_max_iterations=multi_cfg.sub_agent_max_iterations,
        max_parallel_per_step=multi_cfg.max_parallel_per_step,
        security_prompt=config.security_prompt or "",
        callbacks=callbacks,
    ):
        yield msg

    # --- Synthesis phase ---
    async for msg in synthesize(
        llm=llm,
        plan=plan,
        step_results=step_results,
        user_message=message,
        writer=sw,
    ):
        yield msg

    yield sw.stream_end()
