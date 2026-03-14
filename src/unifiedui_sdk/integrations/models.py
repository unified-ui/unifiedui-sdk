"""REST API agent contract models — request/response schemas for external agent integration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageHistoryEntry(BaseModel):
    """A single message in the conversation history.

    Attributes:
        role: The role of the message sender (user, assistant, or system).
        content: The text content of the message.
    """

    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., description="Message text content")


class RestApiAgentInvokeRequest(BaseModel):
    """Standard request body for invoking a REST API agent.

    External REST API agent services that integrate with unified-ui
    must accept this schema on their invoke endpoint.

    Attributes:
        conversation_id: External service's conversation/session ID (None if no conversation creation).
        unified_ui_conversation_id: unified-ui's internal conversation ID.
        message_history: Chat history entries (None when the service manages its own history).
        config: Additional configuration passed through from unified-ui.
    """

    conversation_id: str | None = Field(
        default=None,
        description="External service's conversation/session ID (None without conversation creation)",
    )
    unified_ui_conversation_id: str = Field(
        ...,
        description="unified-ui's internal conversation ID",
    )
    message_history: list[MessageHistoryEntry] | None = Field(
        default=None,
        description="Chat history (None when service manages its own history)",
    )
    config: dict[str, object] = Field(
        default_factory=dict,
        description="Additional configuration for the agent invocation",
    )


class CreateConversationRequest(BaseModel):
    """Standard request body for creating a conversation/session on an external REST API agent.

    Attributes:
        config: Optional configuration for session initialization.
    """

    config: dict[str, object] = Field(
        default_factory=dict,
        description="Optional configuration for session initialization",
    )


class CreateConversationResponse(BaseModel):
    """Standard response from creating a conversation/session on an external REST API agent.

    Attributes:
        conversation_id: The external service's conversation/session ID.
    """

    conversation_id: str = Field(
        ...,
        description="External service's conversation/session ID",
    )
