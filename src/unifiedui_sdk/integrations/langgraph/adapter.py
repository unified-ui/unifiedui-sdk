"""LangGraph stream adapter — wraps a compiled LangGraph graph for unified-ui SSE streaming."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unifiedui_sdk.integrations.base import BaseStreamAdapter

if TYPE_CHECKING:
    from unifiedui_sdk.tracing.langgraph import UnifiedUILanggraphTracer


_INTERNAL_NODES: frozenset[str] = frozenset({"__start__", "__end__"})


class LanggraphStreamAdapter(BaseStreamAdapter):
    """Wraps a compiled LangGraph graph for streaming via the unified-ui SSE protocol.

    Takes a pre-compiled LangGraph ``CompiledGraph`` and maps ``astream_events``
    to unified-ui ``StreamMessage`` objects.  Internal graph nodes
    (``__start__``, ``__end__``) are automatically filtered out.

    Usage::

        graph = builder.compile()
        adapter = LanggraphStreamAdapter(graph=graph)
        async for msg in adapter.stream("What is the weather?"):
            yield msg.model_dump_json()

    Args:
        graph: A compiled LangGraph graph.
        tracer: Optional LangGraph tracer for unified-ui tracing.
    """

    def __init__(
        self,
        graph: Any,
        *,
        tracer: UnifiedUILanggraphTracer | None = None,
    ) -> None:
        """Initialize the adapter.

        Args:
            graph: A compiled LangGraph graph (``CompiledGraph``).
            tracer: Optional LangGraph tracer for unified-ui tracing.
        """
        super().__init__(runnable=graph, tracer=tracer)

    def _skip_event(self, event: dict[str, Any]) -> bool:
        """Skip internal LangGraph nodes (__start__, __end__).

        Args:
            event: A single event from ``astream_events``.

        Returns:
            True if the event belongs to an internal node.
        """
        return event.get("name", "") in _INTERNAL_NODES
