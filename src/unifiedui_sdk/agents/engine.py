"""ReACT agent engine — unified agent with single and multi-agent modes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unifiedui_sdk.streaming.models import StreamMessage, StreamMessageType
from unifiedui_sdk.streaming.writer import StreamWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from langchain_core.language_models import BaseChatModel
    from langchain_core.tools import BaseTool

    from unifiedui_sdk.agents.config import ReActAgentConfig
    from unifiedui_sdk.tracing.react_agent import ReActAgentTracer


class ReActAgentEngine:
    """Unified ReACT agent engine with optional multi-agent orchestration.

    Supports two modes:

    - **Single-agent** (``multi_agent_enabled=False``): Standard LangGraph ReACT
      agent loop with tool calls and reasoning streaming.
    - **Multi-agent** (``multi_agent_enabled=True``): Orchestrator pipeline with
      planner → parallel executor → synthesizer.

    Usage::

        engine = ReActAgentEngine(
            config=ReActAgentConfig(system_prompt="You are helpful."),
            llm=ChatOpenAI(model="gpt-4o"),
            tools=[search_tool, calc_tool],
        )

        async for msg in engine.invoke_stream("What is 2+2?"):
            print(msg.model_dump_json())

    Args:
        config: Agent configuration.
        llm: LangChain chat model instance.
        tools: Pre-loaded LangChain tools.
        tracer: Optional ReActAgentTracer for tracing + optional streaming.
    """

    def __init__(
        self,
        config: ReActAgentConfig,
        llm: BaseChatModel,
        tools: list[BaseTool],
        *,
        tracer: ReActAgentTracer | None = None,
    ) -> None:
        """Initialize the agent engine.

        Args:
            config: Agent configuration.
            llm: LangChain chat model instance.
            tools: Pre-loaded LangChain tools.
            tracer: Optional tracer for tracing agent execution.
        """
        self._config = config
        self._llm = llm
        self._tools = tools
        self._tracer = tracer
        self._synthesis_parts: list[str] = []

    @property
    def config(self) -> ReActAgentConfig:
        """Return the agent configuration."""
        return self._config

    @property
    def is_multi_agent(self) -> bool:
        """Whether this engine runs in multi-agent mode."""
        return self._config.multi_agent_enabled

    async def invoke_stream(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[StreamMessage]:
        """Stream the agent execution, yielding StreamMessage objects.

        Args:
            message: User message to process.
            history: Optional conversation history as list of {role, content} dicts.

        Yields:
            StreamMessage objects for the unified-ui SSE protocol.
        """
        writer = StreamWriter()
        callbacks: list[Any] = []
        if self._tracer:
            callbacks.append(self._tracer)

        if self._config.multi_agent_enabled:
            async for msg in self._run_multi_agent(message, history, writer, callbacks):
                if self._tracer:
                    self._forward_to_tracer(self._tracer, msg)
                yield msg
        else:
            async for msg in self._run_single_agent(message, history, writer, callbacks):
                yield msg

        if self._tracer:
            trace = self._tracer.get_trace()
            yield writer.trace(trace.to_dict())

    async def invoke(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Execute the agent and return the final text response.

        Args:
            message: User message to process.
            history: Optional conversation history.

        Returns:
            The complete text response from the agent.
        """
        text_parts: list[str] = []
        synthesis_parts: list[str] = []

        async for msg in self.invoke_stream(message, history):
            if msg.type == StreamMessageType.TEXT_STREAM:
                text_parts.append(msg.content)
            elif msg.type == StreamMessageType.SYNTHESIS_STREAM:
                synthesis_parts.append(msg.content)

        if synthesis_parts:
            return "".join(synthesis_parts)
        return "".join(text_parts)

    async def _run_single_agent(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        writer: StreamWriter,
        callbacks: list[Any],
    ) -> AsyncGenerator[StreamMessage]:
        """Run in single-agent mode."""
        from unifiedui_sdk.agents.single import run_single_agent

        async for msg in run_single_agent(
            llm=self._llm,
            tools=self._tools,
            config=self._config,
            message=message,
            history=history,
            writer=writer,
            callbacks=callbacks,
        ):
            yield msg

    async def _run_multi_agent(
        self,
        message: str,
        history: list[dict[str, str]] | None,
        writer: StreamWriter,
        callbacks: list[Any],
    ) -> AsyncGenerator[StreamMessage]:
        """Run in multi-agent orchestration mode."""
        from unifiedui_sdk.agents.multi.orchestrator import run_multi_agent

        async for msg in run_multi_agent(
            llm=self._llm,
            tools=self._tools,
            config=self._config,
            message=message,
            history=history,
            writer=writer,
            callbacks=callbacks,
        ):
            yield msg

    def _forward_to_tracer(self, tracer: ReActAgentTracer, msg: StreamMessage) -> None:
        """Forward stream messages to the tracer for dual-use tracking."""
        msg_type = msg.type

        if msg_type == StreamMessageType.PLAN_START:
            tracer.on_plan_start()
        elif msg_type == StreamMessageType.PLAN_COMPLETE:
            tracer.on_plan_created(msg.config.get("plan", {}))
        elif msg_type == StreamMessageType.SUB_AGENT_START:
            tracer.on_sub_agent_start(
                sub_agent_id=msg.config.get("sub_agent_id", ""),
                name=msg.config.get("sub_agent_name", ""),
                step_number=msg.config.get("step_number", 0),
                tools=msg.config.get("tools", []),
            )
        elif msg_type == StreamMessageType.SUB_AGENT_END:
            tracer.on_sub_agent_end(
                sub_agent_id=msg.config.get("sub_agent_id", ""),
                status=msg.config.get("status", ""),
                result_summary=msg.config.get("result_summary", ""),
            )
        elif msg_type == StreamMessageType.TOOL_CALL_START:
            sub_id = msg.config.get("sub_agent_id")
            if sub_id:
                tracer.on_sub_agent_tool_start(
                    sub_agent_id=sub_id,
                    tool_call_id=msg.config.get("tool_call_id", ""),
                    tool_name=msg.config.get("tool_name", ""),
                    tool_arguments=msg.config.get("tool_arguments", {}),
                )
        elif msg_type == StreamMessageType.TOOL_CALL_END:
            sub_id = msg.config.get("sub_agent_id")
            if sub_id:
                tracer.on_sub_agent_tool_end(
                    tool_call_id=msg.config.get("tool_call_id", ""),
                    tool_status=msg.config.get("tool_status", ""),
                    tool_result=msg.config.get("tool_result"),
                    tool_error=msg.config.get("tool_error"),
                )
        elif msg_type == StreamMessageType.SYNTHESIS_START:
            self._synthesis_parts.clear()
            tracer.on_synthesis_start()
        elif msg_type == StreamMessageType.SYNTHESIS_STREAM:
            self._synthesis_parts.append(msg.content)
        elif msg_type == StreamMessageType.STREAM_END and self._synthesis_parts:
            tracer.on_synthesis_end("".join(self._synthesis_parts))
            self._synthesis_parts.clear()
