"""Tests for M365 Outlook client."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from unifiedui_sdk.tools.m365.outlook import (
    CreateEvent,
    ListMessagesQuery,
    OutlookAPIClient,
    OutlookCapability,
    SendMessage,
)
from unifiedui_sdk.tools.m365.outlook.exceptions import OutlookCapabilityError


class TestOutlookAPIClient:
    """Tests for OutlookAPIClient class."""

    @pytest.fixture()
    def mock_auth(self) -> MagicMock:
        """Create mock auth provider."""
        mock = MagicMock()
        mock.get_headers.return_value = {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json",
        }
        return mock

    @pytest.fixture()
    def full_client(self, mock_auth: MagicMock) -> OutlookAPIClient:
        """Create client with all capabilities."""
        return OutlookAPIClient(mock_auth)

    @pytest.fixture()
    def readonly_client(self, mock_auth: MagicMock) -> OutlookAPIClient:
        """Create client with read-only capabilities."""
        return OutlookAPIClient(
            mock_auth,
            capabilities=[
                OutlookCapability.MAIL_READ,
                OutlookCapability.CALENDAR_READ,
            ],
        )

    def test_enabled_capabilities_default(
        self, full_client: OutlookAPIClient
    ) -> None:
        """All capabilities enabled by default."""
        caps = full_client.enabled_capabilities
        assert OutlookCapability.MAIL_READ in caps
        assert OutlookCapability.MAIL_SEND in caps
        assert OutlookCapability.CALENDAR_WRITE in caps

    def test_enabled_capabilities_restricted(
        self, readonly_client: OutlookAPIClient
    ) -> None:
        """Only specified capabilities enabled."""
        caps = readonly_client.enabled_capabilities
        assert OutlookCapability.MAIL_READ in caps
        assert OutlookCapability.MAIL_SEND not in caps

    def test_capability_enforcement_blocks_send(
        self, readonly_client: OutlookAPIClient
    ) -> None:
        """Capability enforcement blocks write operations."""
        with pytest.raises(OutlookCapabilityError):
            readonly_client.messages.send(
                "user-id",
                SendMessage(
                    to=["test@example.com"], subject="Test", body="Body"
                ),
            )

    def test_services_exist(self, full_client: OutlookAPIClient) -> None:
        """Client has expected services."""
        assert hasattr(full_client, "messages")
        assert hasattr(full_client, "calendar")


class TestOutlookCapability:
    """Tests for OutlookCapability enum."""

    def test_all_capabilities(self) -> None:
        """Verify all capabilities are defined."""
        assert OutlookCapability.MAIL_READ.value == "mail_read"
        assert OutlookCapability.MAIL_SEND.value == "mail_send"
        assert OutlookCapability.MAIL_MANAGE.value == "mail_manage"
        assert OutlookCapability.CALENDAR_READ.value == "calendar_read"
        assert OutlookCapability.CALENDAR_WRITE.value == "calendar_write"


class TestOutlookModels:
    """Tests for Outlook model dataclasses."""

    def test_send_message_required_fields(self) -> None:
        """SendMessage requires to, subject, body."""
        msg = SendMessage(
            to=["test@example.com"], subject="Hi", body="Hello world"
        )

        assert msg.to == ["test@example.com"]
        assert msg.subject == "Hi"
        assert msg.body == "Hello world"

    def test_send_message_defaults(self) -> None:
        """SendMessage with default values."""
        msg = SendMessage(
            to=["test@example.com"], subject="Hi", body="Hello"
        )

        assert msg.cc is None
        assert msg.bcc is None
        assert msg.importance == "normal"
        assert msg.save_to_sent is True

    def test_create_event_required_fields(self) -> None:
        """CreateEvent requires core fields."""
        event = CreateEvent(
            subject="Event",
            start=datetime(2024, 1, 15, 10, 0, 0),
            end=datetime(2024, 1, 15, 11, 0, 0),
            timezone="UTC",
        )

        assert event.subject == "Event"
        assert event.timezone == "UTC"

    def test_create_event_with_attendees(self) -> None:
        """CreateEvent with attendees."""
        event = CreateEvent(
            subject="Meeting",
            start=datetime(2024, 1, 15, 10, 0, 0),
            end=datetime(2024, 1, 15, 11, 0, 0),
            timezone="UTC",
            attendees=["person@example.com"],
        )

        assert event.attendees == ["person@example.com"]

    def test_list_messages_query_defaults(self) -> None:
        """ListMessagesQuery default values."""
        query = ListMessagesQuery()

        assert query.top == 25
        assert query.skip == 0
        assert query.filter_query is None

    def test_list_messages_query_custom(self) -> None:
        """ListMessagesQuery with custom values."""
        query = ListMessagesQuery(
            top=50,
            skip=10,
            filter_query="isRead eq false",
            select_fields=["id", "subject"],
        )

        assert query.top == 50
        assert query.filter_query == "isRead eq false"
