"""Message service for Outlook API operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from unifiedui_sdk.tools.m365.core.models import PagedResult, build_paged_result
from unifiedui_sdk.tools.m365.outlook.capabilities import (
    OutlookCapability,
    requires_capability,
)
from unifiedui_sdk.tools.m365.outlook.formatters import (
    format_attachment,
    format_recipient,
)
from unifiedui_sdk.tools.m365.outlook.models import (
    ListMessagesQuery,
    ReplyMessage,
    SearchMessagesQuery,
    SendMessage,
)

if TYPE_CHECKING:
    import builtins

    from unifiedui_sdk.tools.m365.core.http import GraphRequestHandler


class _MessageOperations:
    """Core message operations (shared by user and ``/me``)."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[OutlookCapability],
    ) -> None:
        self._http = http
        self._capabilities = capabilities

    @requires_capability(OutlookCapability.MAIL_SEND)
    def send(self, base: str, message: SendMessage) -> dict[str, Any]:
        """Send an e-mail."""
        payload: dict[str, Any] = {
            "subject": message.subject,
            "body": {
                "contentType": message.body_type,
                "content": message.body,
            },
            "toRecipients": [format_recipient(recipient) for recipient in message.to],
        }

        if message.cc:
            payload["ccRecipients"] = [format_recipient(recipient) for recipient in message.cc]
        if message.bcc:
            payload["bccRecipients"] = [format_recipient(recipient) for recipient in message.bcc]
        if message.importance != "normal":
            payload["importance"] = message.importance
        if message.attachments:
            payload["attachments"] = [format_attachment(attachment) for attachment in message.attachments]

        body: dict[str, Any] = {
            "message": payload,
            "saveToSentItems": message.save_to_sent,
        }

        return self._http.request("POST", f"{base}/sendMail", json_body=body)

    @requires_capability(OutlookCapability.MAIL_SEND)
    def reply(
        self,
        base: str,
        message_id: str,
        reply: ReplyMessage,
    ) -> dict[str, Any]:
        """Reply (or reply-all) to a message."""
        action = "replyAll" if reply.reply_all else "reply"
        return self._http.request(
            "POST",
            f"{base}/messages/{message_id}/{action}",
            json_body={"comment": reply.body},
        )

    @requires_capability(OutlookCapability.MAIL_READ)
    def list(
        self,
        base: str,
        query: ListMessagesQuery | None = None,
    ) -> PagedResult:
        """List messages from a folder."""
        current = query or ListMessagesQuery()

        params: dict[str, Any] = {
            "$top": current.top,
            "$skip": current.skip,
            "$orderby": current.order_by,
        }
        if current.filter_query:
            params["$filter"] = current.filter_query
        if current.search_query:
            params["$search"] = f'"{current.search_query}"'
        if current.select_fields:
            params["$select"] = ",".join(current.select_fields)

        data = self._http.request(
            "GET",
            f"{base}/mailFolders/{current.folder}/messages",
            params=params,
        )
        return build_paged_result(data, current.top, current.skip)

    @requires_capability(OutlookCapability.MAIL_READ)
    def get(
        self,
        base: str,
        message_id: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a single message by ID."""
        params = None
        if select_fields:
            params = {"$select": ",".join(select_fields)}

        return self._http.request(
            "GET",
            f"{base}/messages/{message_id}",
            params=params,
        )

    @requires_capability(OutlookCapability.MAIL_READ)
    def search(
        self,
        base: str,
        query: SearchMessagesQuery,
    ) -> PagedResult:
        """Search messages using KQL syntax."""
        params: dict[str, Any] = {
            "$search": f'"{query.query}"',
            "$top": query.top,
        }
        if query.skip:
            params["$skip"] = query.skip
        if query.select_fields:
            params["$select"] = ",".join(query.select_fields)

        data = self._http.request("GET", f"{base}/messages", params=params)
        return build_paged_result(data, query.top, query.skip)

    @requires_capability(OutlookCapability.MAIL_READ)
    def list_folders(self, base: str) -> PagedResult:
        """List all mail folders."""
        data = self._http.request("GET", f"{base}/mailFolders")
        return build_paged_result(data, top=0, skip=0)

    @requires_capability(OutlookCapability.MAIL_MANAGE)
    def move(
        self,
        base: str,
        message_id: str,
        destination_folder_id: str,
    ) -> dict[str, Any]:
        """Move a message to another folder."""
        return self._http.request(
            "POST",
            f"{base}/messages/{message_id}/move",
            json_body={"destinationId": destination_folder_id},
        )

    @requires_capability(OutlookCapability.MAIL_MANAGE)
    def delete(self, base: str, message_id: str) -> dict[str, Any]:
        """Delete a message."""
        return self._http.request("DELETE", f"{base}/messages/{message_id}")


class _MeMessageService:
    """Message operations scoped to the ``/me`` endpoint."""

    def __init__(self, ops: _MessageOperations) -> None:
        self._ops = ops
        self._capabilities = ops._capabilities

    def send(self, message: SendMessage) -> dict[str, Any]:
        """Send an e-mail as the current user."""
        return self._ops.send("/me", message)

    def reply(self, message_id: str, reply: ReplyMessage) -> dict[str, Any]:
        """Reply to a message as the current user."""
        return self._ops.reply("/me", message_id, reply)

    def list(self, query: ListMessagesQuery | None = None) -> PagedResult:
        """List messages for the current user."""
        return self._ops.list("/me", query)

    def get(
        self,
        message_id: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a message by ID for the current user."""
        return self._ops.get("/me", message_id, select_fields)

    def search(self, query: SearchMessagesQuery) -> PagedResult:
        """Search messages for the current user."""
        return self._ops.search("/me", query)

    def list_folders(self) -> PagedResult:
        """List mail folders for the current user."""
        return self._ops.list_folders("/me")

    def move(self, message_id: str, destination_folder_id: str) -> dict[str, Any]:
        """Move a message for the current user."""
        return self._ops.move("/me", message_id, destination_folder_id)

    def delete(self, message_id: str) -> dict[str, Any]:
        """Delete a message for the current user."""
        return self._ops.delete("/me", message_id)


class MessageService:
    """Outlook message operations."""

    def __init__(
        self,
        http: GraphRequestHandler,
        capabilities: set[OutlookCapability],
    ) -> None:
        """Initialize the message service.

        Args:
            http: HTTP request handler for Graph API.
            capabilities: Set of enabled capabilities.
        """
        self._ops = _MessageOperations(http, capabilities)
        self._capabilities = capabilities
        self.me = _MeMessageService(self._ops)

    def send(self, user: str, message: SendMessage) -> dict[str, Any]:
        """Send an e-mail for a specific user."""
        return self._ops.send(f"/users/{user}", message)

    def reply(
        self,
        user: str,
        message_id: str,
        reply: ReplyMessage,
    ) -> dict[str, Any]:
        """Reply to a message for a specific user."""
        return self._ops.reply(f"/users/{user}", message_id, reply)

    def list(
        self,
        user: str,
        query: ListMessagesQuery | None = None,
    ) -> PagedResult:
        """List messages for a specific user."""
        return self._ops.list(f"/users/{user}", query)

    def get(
        self,
        user: str,
        message_id: str,
        select_fields: builtins.list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a message by ID for a specific user."""
        return self._ops.get(f"/users/{user}", message_id, select_fields)

    def search(self, user: str, query: SearchMessagesQuery) -> PagedResult:
        """Search messages for a specific user."""
        return self._ops.search(f"/users/{user}", query)

    def list_folders(self, user: str) -> PagedResult:
        """List mail folders for a specific user."""
        return self._ops.list_folders(f"/users/{user}")

    def move(
        self,
        user: str,
        message_id: str,
        destination_folder_id: str,
    ) -> dict[str, Any]:
        """Move a message for a specific user."""
        return self._ops.move(f"/users/{user}", message_id, destination_folder_id)

    def delete(self, user: str, message_id: str) -> dict[str, Any]:
        """Delete a message for a specific user."""
        return self._ops.delete(f"/users/{user}", message_id)


__all__ = ["MessageService"]
