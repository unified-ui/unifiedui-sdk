"""LangGraph callback tracer — sniffs traces from LangGraph executions."""

from unifiedui_sdk.tracing.base import BaseTracer


class UnifiedUILanggraphTracer(BaseTracer):
    """Traces LangGraph workflow executions into unified-ui Trace objects.

    Automatically filters internal LangGraph nodes (``__start__``, ``__end__``)
    that represent graph bookkeeping and do not carry meaningful trace data.

    Compatible with:
        - ``create_react_agent`` (prebuilt agents from ``langgraph.prebuilt``)
        - Compiled ``StateGraph`` graphs
        - Any LangGraph graph that accepts ``BaseCallbackHandler`` callbacks

    Usage::

        tracer = UnifiedUILanggraphTracer()
        result = graph.invoke(
            {"messages": [HumanMessage(content="Hello")]},
            config={"callbacks": [tracer]},
        )
        trace = tracer.get_trace()
        trace_dict = trace.to_dict()
    """

    _INTERNAL_NODES: frozenset[str] = frozenset({"__start__", "__end__"})

    def _should_trace_node(self, name: str) -> bool:
        """Skip internal LangGraph graph nodes."""
        return name not in self._INTERNAL_NODES
