"""Tracing data models — mirrors the unified-ui agent-service trace structures."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — needed at runtime by Pydantic
from enum import StrEnum

from pydantic import BaseModel, Field

from unifiedui_sdk.core.utils import generate_id, utc_now


class NodeStatus(StrEnum):
    """Status of a trace node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class NodeType(StrEnum):
    """Type of a trace node."""

    AGENT = "agent"
    TOOL = "tool"
    LLM = "llm"
    CHAIN = "chain"
    RETRIEVER = "retriever"
    WORKFLOW = "workflow"
    FUNCTION = "function"
    HTTP = "http"
    CODE = "code"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    CUSTOM = "custom"
    MEMORY = "memory"
    VECTOR_STORE = "vector_store"
    EMBEDDING = "embedding"
    OUTPUT_PARSER = "output_parser"
    DOCUMENT = "document"
    TEXT_SPLITTER = "text_splitter"
    APP = "app"
    DATA_TRANSFORM = "data_transform"
    QUEUE = "queue"
    DATABASE = "database"


class TraceContextType(StrEnum):
    """Context type for a trace."""

    CONVERSATION = "conversation"
    AUTONOMOUS_AGENT = "autonomous_agent"


class NodeDataIO(BaseModel):
    """Input or output data for a trace node."""

    text: str = ""
    extra_data: dict[str, object] = Field(default_factory=dict, alias="extraData")
    metadata: dict[str, object] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class NodeData(BaseModel):
    """Input/output pair for a trace node."""

    input: NodeDataIO | None = None
    output: NodeDataIO | None = None


class TraceNode(BaseModel):
    """A single node in the trace tree (recursive)."""

    id: str = Field(default_factory=generate_id)
    name: str
    type: NodeType
    reference_id: str = Field(default="", alias="referenceId")
    start_at: datetime | None = Field(default=None, alias="startAt")
    end_at: datetime | None = Field(default=None, alias="endAt")
    duration: float = 0.0
    status: NodeStatus = NodeStatus.PENDING
    logs: list[str] = Field(default_factory=list)
    data: NodeData | None = None
    nodes: list[TraceNode] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    created_by: str = Field(default="", alias="createdBy")
    updated_by: str = Field(default="", alias="updatedBy")

    model_config = {"populate_by_name": True}

    def _finalize(self, status: NodeStatus) -> None:
        """Set final status, end time, and calculate duration."""
        self.status = status
        self.end_at = utc_now()
        self.updated_at = utc_now()
        if self.start_at is not None:
            self.duration = (self.end_at - self.start_at).total_seconds()

    def mark_running(self) -> None:
        """Mark this node as running and set start time."""
        self.status = NodeStatus.RUNNING
        self.start_at = utc_now()
        self.updated_at = utc_now()

    def mark_completed(self) -> None:
        """Mark this node as completed and calculate duration."""
        self._finalize(NodeStatus.COMPLETED)

    def mark_failed(self, error: str | None = None) -> None:
        """Mark this node as failed and optionally log the error.

        Args:
            error: Optional error message to append to logs.
        """
        self._finalize(NodeStatus.FAILED)
        if error:
            self.logs.append(error)

    def add_child(self, node: TraceNode) -> None:
        """Add a child node.

        Args:
            node: The child TraceNode to add.
        """
        self.nodes.append(node)
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, object]:
        """Serialize to a camelCase dict matching the agent-service JSON format."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class Trace(BaseModel):
    """A complete trace for a workflow execution."""

    id: str = Field(default_factory=generate_id)
    tenant_id: str = Field(default="", alias="tenantId")
    chat_agent_id: str = Field(default="", alias="chatAgentId")
    conversation_id: str = Field(default="", alias="conversationId")
    autonomous_agent_id: str = Field(default="", alias="autonomousAgentId")
    context_type: TraceContextType = Field(default=TraceContextType.CONVERSATION, alias="contextType")
    reference_id: str = Field(default="", alias="referenceId")
    reference_name: str = Field(default="", alias="referenceName")
    reference_metadata: dict[str, object] = Field(default_factory=dict, alias="referenceMetadata")
    logs: list[str] = Field(default_factory=list)
    nodes: list[TraceNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")
    created_by: str = Field(default="", alias="createdBy")
    updated_by: str = Field(default="", alias="updatedBy")

    model_config = {"populate_by_name": True}

    def add_node(self, node: TraceNode) -> None:
        """Add a top-level node to the trace.

        Args:
            node: The TraceNode to add.
        """
        self.nodes.append(node)
        self.updated_at = utc_now()

    def add_log(self, message: str) -> None:
        """Append a log message.

        Args:
            message: Log message to append.
        """
        self.logs.append(message)
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, object]:
        """Serialize to a camelCase dict matching the agent-service JSON format."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)
