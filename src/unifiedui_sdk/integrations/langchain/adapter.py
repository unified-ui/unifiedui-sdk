"""LangChain stream adapter — wraps a LangChain Runnable for unified-ui SSE streaming."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unifiedui_sdk.integrations.base import BaseStreamAdapter

if TYPE_CHECKING:
    from unifiedui_sdk.tracing.langchain import UnifiedUILangchainTracer


class LangchainStreamAdapter(BaseStreamAdapter):
    """Wraps a pre-built LangChain agent/runnable for unified-ui SSE streaming.

    Takes any LangChain-compatible runnable that supports ``astream_events``
    and maps the events to unified-ui ``StreamMessage`` objects.

    Usage::

        from langgraph.prebuilt import create_react_agent

        agent = create_react_agent(llm, tools)
        adapter = LangchainStreamAdapter(agent=agent)
        async for msg in adapter.stream("What is the weather?"):
            yield msg.model_dump_json()

    Args:
        agent: A pre-built LangChain agent/runnable with ``astream_events`` support.
        tracer: Optional LangChain tracer for unified-ui tracing.
    """

    def __init__(
        self,
        agent: Any,
        *,
        tracer: UnifiedUILangchainTracer | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            agent: A pre-built LangChain agent/runnable.
            tracer: Optional LangChain tracer for unified-ui tracing.
        """
        super().__init__(runnable=agent, tracer=tracer)
