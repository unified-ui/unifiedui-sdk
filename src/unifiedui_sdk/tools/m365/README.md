# unifiedui_sdk.tools.m365

Microsoft 365 Graph API clients with capability-based access control for building AI agents.

## Contents

| Module | Description |
|--------|-------------|
| `core/` | Shared authentication, HTTP handling, exceptions, and pagination |
| `global_search/` | Cross-tenant search across Outlook, SharePoint, Teams |
| `outlook/` | Email and calendar operations |
| `sharepoint/` | Sites, drives, pages, lists, OneNote, and search |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Core Module                              │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ GraphAuthProvider│  │GraphRequestHandler│  │  PagedResult  │  │
│  │  + get_headers() │  │  + request()     │  │  + next_link  │  │
│  │  + MSAL/Azure ID │  │  + request_url() │  │  + items      │  │
│  └─────────────────┘  │  + request_raw() │  └───────────────┘  │
│                       │  + upload_bytes()│                      │
│                       └──────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
    ┌──────┴──────┐      ┌──────┴──────┐      ┌──────┴──────┐
    │ GlobalSearch│      │   Outlook   │      │  SharePoint │
    │   Client    │      │   Client    │      │   Client    │
    │  .search    │      │  .messages  │      │  .sites     │
    │             │      │  .calendar  │      │  .drives    │
    │             │      │             │      │  .pages     │
    │             │      │             │      │  .lists     │
    │             │      │             │      │  .onenote   │
    │             │      │             │      │  .search    │
    └─────────────┘      └─────────────┘      └─────────────┘
```

## Installation

```bash
pip install unifiedui-sdk[m365]
```

Or with uv:

```bash
uv add unifiedui-sdk --extra m365
```

## Authentication

All clients use `GraphAuthProvider` which supports:

1. **MSAL ConfidentialClientApplication** (client credentials flow)
2. **Azure Identity TokenCredential** (DefaultAzureCredential, etc.)

```python
from unifiedui_sdk.tools.m365.core import GraphAuthProvider

# Option 1: MSAL with client credentials
auth = GraphAuthProvider(
    tenant_id="your-tenant-id",
    client_id="your-client-id",
    client_secret="your-client-secret",
)

# Option 2: Azure Identity TokenCredential
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
auth = GraphAuthProvider(credential=credential)
```

---

## Outlook Client

Email and calendar operations with granular capability control.

### Capabilities

| Capability | Description |
|------------|-------------|
| `MAIL_READ` | Read emails and attachments |
| `MAIL_SEND` | Send emails |
| `MAIL_MANAGE` | Move, delete, flag emails |
| `CALENDAR_READ` | Read calendar events |
| `CALENDAR_WRITE` | Create, update, delete events |

### Usage

```python
from unifiedui_sdk.tools.m365 import (
    OutlookAPIClient,
    OutlookAuthProvider,
    OutlookCapability,
    SendMessage,
    CreateEvent,
    ListMessagesQuery,
)
from datetime import datetime

auth = OutlookAuthProvider(
    tenant_id="...", client_id="...", client_secret="..."
)

client = OutlookAPIClient(
    auth_provider=auth,
    capabilities=[
        OutlookCapability.MAIL_READ,
        OutlookCapability.MAIL_SEND,
        OutlookCapability.CALENDAR_READ,
        OutlookCapability.CALENDAR_WRITE,
    ],
)

# List messages
messages = client.messages.list(
    user_id="user@example.com",
    query=ListMessagesQuery(folder="inbox", top=10),
)
for msg in messages.items:
    print(msg["subject"])

# Send email
client.messages.send(
    user_id="user@example.com",
    message=SendMessage(
        to=["recipient@example.com"],
        subject="Meeting Notes",
        body="<p>Here are the notes...</p>",
    ),
)

# Create calendar event
client.calendar.create_event(
    user_id="user@example.com",
    event=CreateEvent(
        subject="Team Standup",
        start=datetime(2024, 3, 15, 9, 0),
        end=datetime(2024, 3, 15, 9, 30),
        timezone="Europe/Berlin",
    ),
)
```

---

## SharePoint Client

Sites, drives, pages, lists, OneNote, and search operations.

### Capabilities

| Capability | Description |
|------------|-------------|
| `SITES_READ` | Read site information |
| `DRIVES_READ` | Read files and folders |
| `DRIVES_WRITE` | Upload, create, delete files |
| `PAGES_READ` | Read SharePoint pages |
| `PAGES_WRITE` | Create and update pages |
| `LISTS_READ` | Read list items |
| `LISTS_WRITE` | Create, update, delete list items |
| `ONENOTE_READ` | Read OneNote notebooks |

### Usage

```python
from unifiedui_sdk.tools.m365 import (
    SharePointAPIClient,
    SharePointAuthProvider,
    SharePointCapability,
    SiteSearchQuery,
    DriveItemsQuery,
    UploadFile,
)

auth = SharePointAuthProvider(
    tenant_id="...", client_id="...", client_secret="..."
)

client = SharePointAPIClient(
    auth_provider=auth,
    capabilities=[
        SharePointCapability.SITES_READ,
        SharePointCapability.DRIVES_READ,
        SharePointCapability.DRIVES_WRITE,
    ],
)

# Search for sites
sites = client.sites.search(SiteSearchQuery(query="Project Alpha"))
for site in sites.items:
    print(site["displayName"])

# List drive items
items = client.drives.list_items(
    site_id="site-id",
    drive_id="drive-id",
    query=DriveItemsQuery(folder_path="/Documents"),
)

# Upload file
client.drives.upload(
    site_id="site-id",
    drive_id="drive-id",
    upload=UploadFile(
        file_path="/Reports/Q1.pdf",
        content=pdf_bytes,
        content_type="application/pdf",
    ),
)
```

---

## Global Search Client

Cross-tenant search across Microsoft 365 content.

### Entity Types

| Constant | Entities |
|----------|----------|
| `OUTLOOK_ENTITIES` | `message`, `event` |
| `SHAREPOINT_ENTITIES` | `driveItem`, `listItem`, `site`, `page` |
| `TEAMS_ENTITIES` | `chatMessage` |
| `ALL_CONTENT_ENTITIES` | All of the above |

### Usage

```python
from unifiedui_sdk.tools.m365 import (
    GraphSearchClient,
    GraphSearchAuthProvider,
    SearchRequest,
    BatchSearchQuery,
    OUTLOOK_ENTITIES,
    SHAREPOINT_ENTITIES,
)

auth = GraphSearchAuthProvider(
    tenant_id="...", client_id="...", client_secret="..."
)

client = GraphSearchClient(auth_provider=auth)

# Single search
results = client.search.execute(
    SearchRequest(
        query="quarterly report",
        entity_types=SHAREPOINT_ENTITIES,
        size=25,
    )
)

# Batch search (multiple queries in one request)
batch_results = client.search.batch(
    BatchSearchQuery(
        requests=[
            SearchRequest(query="budget 2024", entity_types=SHAREPOINT_ENTITIES),
            SearchRequest(query="meeting notes", entity_types=OUTLOOK_ENTITIES),
        ]
    )
)
```

---

## Pagination

All list operations return `PagedResult` with automatic handling of `@odata.nextLink`:

```python
from unifiedui_sdk.tools.m365.core import PagedResult

# First page
result: PagedResult = client.messages.list(user_id="...", query=query)

# Check for more pages
while result.next_link:
    result = client.messages.list_next(result.next_link)
    for item in result.items:
        process(item)
```

---

## Exceptions

| Exception | Description |
|-----------|-------------|
| `M365ClientError` | Base exception for all M365 errors |
| `M365AuthError` | Authentication failures |
| `M365CapabilityError` | Operation not allowed by enabled capabilities |
| `M365APIError` | Graph API errors (4xx/5xx responses) |

```python
from unifiedui_sdk.tools.m365.core import M365CapabilityError, M365APIError

try:
    client.messages.send(...)
except M365CapabilityError as e:
    print(f"Missing capability: {e}")
except M365APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

---

## Using with ReACT Agent

The M365 clients can be wrapped as LangChain tools for use with the ReACT Agent Engine:

```python
from langchain_core.tools import tool
from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.tools.m365 import (
    OutlookAPIClient,
    OutlookAuthProvider,
    OutlookCapability,
    SendMessage,
)

# Initialize client
auth = OutlookAuthProvider(...)
outlook = OutlookAPIClient(
    auth_provider=auth,
    capabilities=[OutlookCapability.MAIL_SEND],
)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to the specified recipient."""
    outlook.messages.send(
        user_id="me",
        message=SendMessage(to=[to], subject=subject, body=body),
    )
    return f"Email sent to {to}"


config = ReActAgentConfig(system_prompt="You are an email assistant.")
engine = ReActAgentEngine(config=config, llm=llm, tools=[send_email])
```
