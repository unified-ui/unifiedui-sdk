"""Base tracer — shared callback handler logic for all tracer implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langchain_core.callbacks import BaseCallbackHandler

from unifiedui_sdk.core.utils import safe_str, str_uuid, utc_now
from unifiedui_sdk.tracing.models import (
    NodeData,
    NodeDataIO,
    NodeStatus,
    NodeType,
    Trace,
    TraceNode,
)

if TYPE_CHECKING:
    from uuid import UUID

    from langchain_core.agents import AgentAction, AgentFinish
    from langchain_core.documents import Document
    from langchain_core.messages import BaseMessage
    from langchain_core.outputs import ChatGenerationChunk, GenerationChunk, LLMResult


def _extract_name(serialized: dict[str, Any] | None, fallback: str) -> str:
    """Extract a human-readable name from a LangChain serialized dict.

    Args:
        serialized: The serialized component dict (may be None in newer LangChain/LangGraph).
        fallback: Default name if extraction fails.

    Returns:
        Extracted component name.
    """
    if not serialized:
        return fallback
    id_list = serialized.get("id")
    if id_list:
        return str(id_list[-1])
    return str(serialized.get("name", fallback))


class BaseTracer(BaseCallbackHandler):
    """Base tracer with shared node management and callback logic.

    Subclasses can override:
        - ``_resolve_name``: customize how component names are extracted.
        - ``_should_trace_node``: filter which nodes appear in the trace.
    """

    def __init__(self, trace: Trace | None = None) -> None:
        """Initialize the tracer.

        Args:
            trace: Optional pre-configured Trace object. If not provided, a new one is created.
        """
        super().__init__()
        self._trace = trace or Trace()
        self._node_map: dict[str, TraceNode] = {}
        self._parent_map: dict[str, str] = {}

    @property
    def trace(self) -> Trace:
        """Return the current trace object."""
        return self._trace

    def get_trace(self) -> Trace:
        """Return the completed trace object.

        Returns:
            The Trace containing all sniffed nodes.
        """
        return self._trace

    def get_trace_dict(self) -> dict[str, object]:
        """Return the completed trace as a camelCase dict.

        Returns:
            Dict matching the agent-service JSON format.
        """
        return self._trace.to_dict()

    # --- Hooks for subclasses ---

    def _resolve_name(self, serialized: dict[str, Any] | None, fallback: str, **kwargs: Any) -> str:
        """Resolve a human-readable component name.

        Override in subclasses for framework-specific name extraction.

        Args:
            serialized: Serialized component dict from LangChain.
            fallback: Default name when extraction fails.
            **kwargs: Additional callback keyword arguments.

        Returns:
            Resolved component name.
        """
        name = kwargs.get("name")
        if name:
            return str(name)
        return _extract_name(serialized, fallback)

    def _should_trace_node(self, name: str) -> bool:
        """Whether to create a trace node for the given component name.

        Override in subclasses to filter out framework-internal nodes.

        Args:
            name: The resolved component name.

        Returns:
            True if a node should be created, False to skip.
        """
        return True

    # --- Node management ---

    def _create_node(
        self,
        run_id: UUID,
        parent_run_id: UUID | None,
        name: str,
        node_type: NodeType,
        input_text: str = "",
        input_extra: dict[str, object] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> TraceNode | None:
        """Create a new TraceNode and register it in the node map.

        Returns None if the node should be skipped (see ``_should_trace_node``).
        """
        if not self._should_trace_node(name):
            return None

        rid = str_uuid(run_id)
        node = TraceNode(
            id=rid,
            name=name,
            type=node_type,
            status=NodeStatus.RUNNING,
            start_at=utc_now(),
            data=NodeData(
                input=NodeDataIO(
                    text=input_text,
                    extra_data=input_extra or {},
                ),
            ),
            metadata=metadata or {},
        )
        self._node_map[rid] = node

        if parent_run_id:
            pid = str_uuid(parent_run_id)
            if pid in self._node_map:
                self._parent_map[rid] = pid
                self._node_map[pid].add_child(node)
                return node

        self._trace.add_node(node)
        return node

    def _complete_node(
        self,
        run_id: UUID,
        output_text: str = "",
        output_extra: dict[str, object] | None = None,
    ) -> None:
        """Mark a node as completed and set output data."""
        node = self._node_map.get(str_uuid(run_id))
        if node is None:
            return

        if node.data is None:
            node.data = NodeData()
        node.data.output = NodeDataIO(
            text=output_text,
            extra_data=output_extra or {},
        )
        node.mark_completed()

    def _fail_node(self, run_id: UUID, error: str) -> None:
        """Mark a node as failed."""
        node = self._node_map.get(str_uuid(run_id))
        if node is None:
            return
        node.mark_failed(error=error)

    # --- LLM callbacks ---

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM start event."""
        name = self._resolve_name(serialized, "LLM", **kwargs)
        self._create_node(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            node_type=NodeType.LLM,
            input_text="\n---\n".join(prompts),
            metadata={"tags": tags or [], **(metadata or {})},
        )

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle chat model start event."""
        name = self._resolve_name(serialized, "ChatModel", **kwargs)
        formatted_messages: list[str] = []
        for message_group in messages:
            for msg in message_group:
                formatted_messages.append(f"[{msg.type}]: {msg.content}")

        self._create_node(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            node_type=NodeType.LLM,
            input_text="\n".join(formatted_messages),
            metadata={"tags": tags or [], **(metadata or {})},
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM end event."""
        output_text = ""
        extra: dict[str, object] = {}

        if response.generations:
            texts = []
            for gen_list in response.generations:
                for gen in gen_list:
                    texts.append(gen.text if gen.text else safe_str(gen.message if hasattr(gen, "message") else ""))
            output_text = "\n".join(texts)

        if response.llm_output:
            extra["llm_output"] = response.llm_output

        self._complete_node(run_id=run_id, output_text=output_text, output_extra=extra)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle LLM error event."""
        self._fail_node(run_id=run_id, error=safe_str(error))

    def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: GenerationChunk | ChatGenerationChunk | None = None,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle streaming token (no-op for tracing)."""

    # --- Chain callbacks ---

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle chain start event."""
        name = self._resolve_name(serialized, "Chain", **kwargs)
        self._create_node(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            node_type=NodeType.CHAIN,
            input_text=safe_str(inputs),
            metadata={"tags": tags or [], **(metadata or {})},
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle chain end event."""
        self._complete_node(run_id=run_id, output_text=safe_str(outputs))

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle chain error event."""
        self._fail_node(run_id=run_id, error=safe_str(error))

    # --- Tool callbacks ---

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool start event."""
        name = self._resolve_name(serialized, "Tool", **kwargs)
        self._create_node(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            node_type=NodeType.TOOL,
            input_text=input_str,
            metadata={"tags": tags or [], **(metadata or {})},
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool end event."""
        self._complete_node(run_id=run_id, output_text=safe_str(output))

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle tool error event."""
        self._fail_node(run_id=run_id, error=safe_str(error))

    # --- Agent callbacks ---

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle agent action event."""
        node = self._node_map.get(str_uuid(run_id))
        if node:
            node.logs.append(f"Action: {action.tool} | Input: {safe_str(action.tool_input)}")

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle agent finish event."""
        node = self._node_map.get(str_uuid(run_id))
        if node:
            node.logs.append(f"Final output: {safe_str(finish.return_values)}")

    # --- Retriever callbacks ---

    def on_retriever_start(
        self,
        serialized: dict[str, Any],
        query: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle retriever start event."""
        name = self._resolve_name(serialized, "Retriever", **kwargs)
        self._create_node(
            run_id=run_id,
            parent_run_id=parent_run_id,
            name=name,
            node_type=NodeType.RETRIEVER,
            input_text=query,
            metadata={"tags": tags or [], **(metadata or {})},
        )

    def on_retriever_end(
        self,
        documents: list[Document],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle retriever end event."""
        doc_texts = [f"[{i}] {doc.page_content[:200]}" for i, doc in enumerate(documents)]
        self._complete_node(
            run_id=run_id,
            output_text="\n".join(doc_texts),
            output_extra={"document_count": len(documents)},
        )

    def on_retriever_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle retriever error event."""
        self._fail_node(run_id=run_id, error=safe_str(error))

    # --- Text / generic callbacks ---

    def on_text(
        self,
        text: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Handle generic text event (logged to parent node if available)."""
        target_id = str_uuid(parent_run_id) if parent_run_id else str_uuid(run_id)
        node = self._node_map.get(target_id)
        if node:
            node.logs.append(text)
