"""LangChain callback tracer — sniffs traces from LangChain executions."""

from unifiedui_sdk.tracing.base import BaseTracer


class UnifiedUILangchainTracer(BaseTracer):
    """Traces LangChain workflow executions into unified-ui Trace objects.

    Compatible with:
        - ``AgentExecutor`` (legacy agents)
        - LangChain chains (``RunnableSequence``, ``LLMChain``, etc.)
        - Any LangChain component that accepts ``BaseCallbackHandler`` callbacks

    Usage::

        tracer = UnifiedUILangchainTracer()
        result = agent.invoke({"input": "..."}, config={"callbacks": [tracer]})
        trace = tracer.get_trace()
        trace_dict = trace.to_dict()
    """
