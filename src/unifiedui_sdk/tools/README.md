# unifiedui_sdk.tools

Reusable tool clients for building AI agents with unified-ui SDK.

## Contents

| Module | Description |
|--------|-------------|
| `m365/` | Microsoft 365 Graph API clients (Outlook, SharePoint, Global Search) |

## Installation

The tools module requires additional dependencies. Install with the `m365` extra:

```bash
pip install unifiedui-sdk[m365]
```

Or with uv:

```bash
uv add unifiedui-sdk --extra m365
```

## Available Clients

### Microsoft 365 (`m365/`)

Full-featured clients for Microsoft Graph API with capability-based access control:

| Client | Description |
|--------|-------------|
| `OutlookAPIClient` | Email & calendar operations |
| `SharePointAPIClient` | Sites, drives, pages, lists, OneNote |
| `GraphSearchClient` | Cross-tenant search (Outlook, SharePoint, Teams) |

See [`m365/README.md`](m365/README.md) for detailed documentation.

## Quick Start

```python
from unifiedui_sdk.tools.m365 import (
    OutlookAPIClient,
    OutlookAuthProvider,
    OutlookCapability,
    SendMessage,
)

# Create auth provider (uses MSAL or Azure Identity)
auth = OutlookAuthProvider(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

# Create client with specific capabilities
client = OutlookAPIClient(
    auth_provider=auth,
    capabilities=[OutlookCapability.MAIL_READ, OutlookCapability.MAIL_SEND],
)

# Send an email
client.messages.send(
    user_id="user@example.com",
    message=SendMessage(
        to=["recipient@example.com"],
        subject="Hello from unified-ui",
        body="<p>This is a test email.</p>",
    ),
)
```

## Design Principles

1. **Capability-based access control**: Clients enforce permissions at runtime via capability enums
2. **Paginated results**: All list operations return `PagedResult` with automatic `@odata.nextLink` handling
3. **Service-oriented**: Clients expose services (e.g., `.messages`, `.calendar`) for organized API access
4. **Type-safe**: Full type hints with dataclass models for requests and responses
