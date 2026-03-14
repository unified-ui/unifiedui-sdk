"""Tests for REST API agent contract models."""

from __future__ import annotations

import pytest

from unifiedui_sdk.integrations.models import (
    CreateConversationRequest,
    CreateConversationResponse,
    MessageHistoryEntry,
    RestApiAgentInvokeRequest,
)


class TestMessageHistoryEntry:
    """Tests for MessageHistoryEntry model."""

    def test_create_user_message(self) -> None:
        entry = MessageHistoryEntry(role="user", content="Hello")
        assert entry.role == "user"
        assert entry.content == "Hello"

    def test_create_assistant_message(self) -> None:
        entry = MessageHistoryEntry(role="assistant", content="Hi there!")
        assert entry.role == "assistant"
        assert entry.content == "Hi there!"

    def test_create_system_message(self) -> None:
        entry = MessageHistoryEntry(role="system", content="You are helpful.")
        assert entry.role == "system"

    def test_serialization_roundtrip(self) -> None:
        entry = MessageHistoryEntry(role="user", content="test")
        data = entry.model_dump()
        restored = MessageHistoryEntry(**data)
        assert restored == entry

    def test_json_roundtrip(self) -> None:
        entry = MessageHistoryEntry(role="user", content="test")
        json_str = entry.model_dump_json()
        restored = MessageHistoryEntry.model_validate_json(json_str)
        assert restored == entry


class TestRestApiAgentInvokeRequest:
    """Tests for RestApiAgentInvokeRequest model."""

    def test_minimal_request(self) -> None:
        req = RestApiAgentInvokeRequest(unified_ui_conversation_id="conv-123")
        assert req.conversation_id is None
        assert req.unified_ui_conversation_id == "conv-123"
        assert req.message_history is None
        assert req.config == {}

    def test_full_request(self) -> None:
        history = [
            MessageHistoryEntry(role="user", content="Hi"),
            MessageHistoryEntry(role="assistant", content="Hello!"),
        ]
        req = RestApiAgentInvokeRequest(
            conversation_id="ext-456",
            unified_ui_conversation_id="conv-123",
            message_history=history,
            config={"temperature": 0.7},
        )
        assert req.conversation_id == "ext-456"
        assert req.unified_ui_conversation_id == "conv-123"
        assert len(req.message_history) == 2  # type: ignore[arg-type]
        assert req.config == {"temperature": 0.7}

    def test_null_history_when_service_manages(self) -> None:
        req = RestApiAgentInvokeRequest(
            conversation_id="ext-789",
            unified_ui_conversation_id="conv-123",
            message_history=None,
        )
        assert req.message_history is None

    def test_empty_history_list(self) -> None:
        req = RestApiAgentInvokeRequest(
            unified_ui_conversation_id="conv-123",
            message_history=[],
        )
        assert req.message_history == []

    def test_serialization_roundtrip(self) -> None:
        req = RestApiAgentInvokeRequest(
            conversation_id="ext-1",
            unified_ui_conversation_id="conv-1",
            message_history=[MessageHistoryEntry(role="user", content="test")],
            config={"key": "value"},
        )
        data = req.model_dump()
        restored = RestApiAgentInvokeRequest(**data)
        assert restored == req

    def test_json_roundtrip(self) -> None:
        req = RestApiAgentInvokeRequest(
            unified_ui_conversation_id="conv-1",
            config={"key": "value"},
        )
        json_str = req.model_dump_json()
        restored = RestApiAgentInvokeRequest.model_validate_json(json_str)
        assert restored == req

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(Exception):
            RestApiAgentInvokeRequest()  # type: ignore[call-arg]


class TestCreateConversationRequest:
    """Tests for CreateConversationRequest model."""

    def test_default_empty_config(self) -> None:
        req = CreateConversationRequest()
        assert req.config == {}

    def test_with_config(self) -> None:
        req = CreateConversationRequest(config={"agent_id": "abc"})
        assert req.config == {"agent_id": "abc"}


class TestCreateConversationResponse:
    """Tests for CreateConversationResponse model."""

    def test_create_response(self) -> None:
        resp = CreateConversationResponse(conversation_id="session-xyz")
        assert resp.conversation_id == "session-xyz"

    def test_missing_conversation_id_raises(self) -> None:
        with pytest.raises(Exception):
            CreateConversationResponse()  # type: ignore[call-arg]

    def test_json_roundtrip(self) -> None:
        resp = CreateConversationResponse(conversation_id="session-1")
        json_str = resp.model_dump_json()
        restored = CreateConversationResponse.model_validate_json(json_str)
        assert restored == resp
