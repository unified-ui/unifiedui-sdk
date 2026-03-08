# ADR-001: Streaming-Konzept — Reasoning & Tool Calls

**Status:** Draft
**Datum:** 2026-03-07
**Autor:** Enrico Goerlitz

---

## 1. Status Quo

### Agent-Service SSE-Protokoll (4 Event-Types)

| SSE Event | Verwendung |
|-----------|-----------|
| `event: message` | Hauptkanal — `StreamMessage` JSON |
| `event: trace` | Trace-Daten (Frontend ignoriert diese aktuell) |
| `event: error` | Fehler (Frontend ignoriert diese aktuell) |
| `event: done` | Stream-Ende-Signal (Frontend ignoriert diese aktuell) |

### StreamMessage-Typen (7)

| Type | Zweck |
|------|-------|
| `STREAM_START` | Stream beginnt, enthält config |
| `TEXT_STREAM` | Token-Chunk (delta) |
| `STREAM_NEW_MESSAGE` | Neue Nachricht-Boundary |
| `STREAM_END` | Token-Streaming beendet |
| `MESSAGE_COMPLETE` | Finale Nachricht mit Metadaten |
| `TITLE_GENERATION` | Konversations-Titel |
| `ERROR` | Fehlermeldung |

### Wire-Format

```
event: message
data: {"type":"TEXT_STREAM","content":"Hello","config":{}}
```

### Lücken im aktuellen System

- Kein Reasoning-Support (Thinking-Tokens von o1/o3/Claude werden nicht angezeigt)
- Tool-Call-Visualisierung fehlt komplett (weder Name, Argumente noch Ergebnis)
- Foundry: `workflow_action` Items enthalten nur Metadaten (`action_id`, `kind`, `status`) — kein Input/Output-Content
- Frontend verarbeitet nur `event: message` — `trace`, `error`, `done` werden ignoriert

---

## 2. Neue StreamMessage-Typen

Erweiterung des `StreamMessageType`-Enums um **6 neue Typen** (Single-Agent) + **8 weitere für Multi-Agent** (→ [ADR-002](002_RE_ACT_AGENT_ENGINE.md)):

### Single-Agent Events

| Neuer Type | Zweck |
|------------|-------|
| `REASONING_START` | Reasoning-Phase beginnt |
| `REASONING_STREAM` | Reasoning-Token-Chunk (delta) |
| `REASONING_END` | Reasoning-Phase beendet |
| `TOOL_CALL_START` | Tool-Call beginnt (Name + Argumente) |
| `TOOL_CALL_STREAM` | Tool-Call Ergebnis-Streaming (delta) |
| `TOOL_CALL_END` | Tool-Call abgeschlossen (Status + Ergebnis) |

### Multi-Agent Events (→ ADR-002)

| Neuer Type | Zweck |
|------------|-------|
| `PLAN_START` | Orchestrator beginnt Planung |
| `PLAN_STREAM` | Plan-Reasoning (delta) |
| `PLAN_COMPLETE` | Fertiger ExecutionPlan als JSON |
| `SUB_AGENT_START` | Sub-Agent beginnt Ausführung |
| `SUB_AGENT_STREAM` | Sub-Agent Text-Chunk (delta) |
| `SUB_AGENT_END` | Sub-Agent-Ergebnis abgeschlossen |
| `SYNTHESIS_START` | Synthese-Phase beginnt |
| `SYNTHESIS_STREAM` | Synthese Text-Chunk (delta) — finaler Antwort-Stream |

START/STREAM/END-Symmetrie ermöglicht dem Frontend präzises State-Management (Loading-Indicator, Animation, Collapsible-Toggle).

> **Hinweis:** `TOOL_CALL_START/END` im Multi-Agent-Modus tragen ein zusätzliches `sub_agent_id`-Feld in `config`, um den Tool-Call dem richtigen Sub-Agent zuzuordnen. Details in [ADR-002](002_RE_ACT_AGENT_ENGINE.md#7-streaming-multi-agent).

### Vollständiger Lifecycle eines Agent-Streams mit Reasoning + Tool Calls

```
STREAM_START
├── REASONING_START
│   ├── REASONING_STREAM  ("Ich muss die Datenbank durchsuchen...")
│   ├── REASONING_STREAM  ("Der User fragt nach Dokumenten...")
│   └── REASONING_END
├── TOOL_CALL_START       {tool_call_id, tool_name, tool_arguments}
│   ├── TOOL_CALL_STREAM  (optional — für große Tool-Ergebnisse)
│   └── TOOL_CALL_END     {tool_call_id, tool_name, tool_status, tool_result}
├── TOOL_CALL_START       (zweiter Tool-Call, falls nötig)
│   └── TOOL_CALL_END
├── TEXT_STREAM           ("Basierend auf den Ergebnissen...")
├── TEXT_STREAM           ("...hier ist die Antwort.")
├── STREAM_END
└── MESSAGE_COMPLETE      {full message + metadata}
```

### Einfacher Chat (kein Reasoning, keine Tools) — backward-compatible

```
STREAM_START
├── TEXT_STREAM  ("Hello")
├── TEXT_STREAM  (" World")
├── STREAM_END
└── MESSAGE_COMPLETE
```

---

## 3. JSON-Payloads

**StreamMessage-Struktur bleibt gleich** — `config` wird für strukturierte Daten genutzt:

```typescript
interface StreamMessage {
  type: StreamMessageType;
  content: string;
  config: Record<string, any>;
}
```

### REASONING_START

```json
{
  "type": "REASONING_START",
  "content": "",
  "config": {}
}
```

### REASONING_STREAM

```json
{
  "type": "REASONING_STREAM",
  "content": "Ich muss die Datenbank durchsuchen, weil...",
  "config": {}
}
```

### REASONING_END

```json
{
  "type": "REASONING_END",
  "content": "",
  "config": {}
}
```

### TOOL_CALL_START

```json
{
  "type": "TOOL_CALL_START",
  "content": "",
  "config": {
    "tool_call_id": "tc_abc123",
    "tool_name": "search_knowledge_base",
    "tool_arguments": {
      "query": "unified-ui architecture",
      "top_k": 5
    }
  }
}
```

### TOOL_CALL_STREAM (optional, für große Ergebnisse)

```json
{
  "type": "TOOL_CALL_STREAM",
  "content": "partial result chunk...",
  "config": {
    "tool_call_id": "tc_abc123"
  }
}
```

### TOOL_CALL_END (Erfolg)

```json
{
  "type": "TOOL_CALL_END",
  "content": "",
  "config": {
    "tool_call_id": "tc_abc123",
    "tool_name": "search_knowledge_base",
    "tool_status": "success",
    "tool_result": "Found 3 documents: [1] Architecture Overview, [2] API Reference, [3] Deployment Guide",
    "tool_duration_ms": 342
  }
}
```

### TOOL_CALL_END (Fehler)

```json
{
  "type": "TOOL_CALL_END",
  "content": "",
  "config": {
    "tool_call_id": "tc_abc123",
    "tool_name": "search_knowledge_base",
    "tool_status": "error",
    "tool_error": "Connection timeout after 5000ms",
    "tool_duration_ms": 5002
  }
}
```

---

## 4. Agent-Service Implementierung (Go)

### 4.1 Neue StreamMessageType-Konstanten

```go
// internal/domain/models/stream.go
const (
    StreamMessageTypeStreamStart      = "STREAM_START"
    StreamMessageTypeTextStream       = "TEXT_STREAM"
    StreamMessageTypeStreamNewMessage = "STREAM_NEW_MESSAGE"
    StreamMessageTypeStreamEnd        = "STREAM_END"
    StreamMessageTypeMessageComplete  = "MESSAGE_COMPLETE"
    StreamMessageTypeTitleGeneration  = "TITLE_GENERATION"
    StreamMessageTypeError            = "ERROR"

    // NEU
    StreamMessageTypeReasoningStart  = "REASONING_START"
    StreamMessageTypeReasoningStream = "REASONING_STREAM"
    StreamMessageTypeReasoningEnd    = "REASONING_END"
    StreamMessageTypeToolCallStart   = "TOOL_CALL_START"
    StreamMessageTypeToolCallStream  = "TOOL_CALL_STREAM"
    StreamMessageTypeToolCallEnd     = "TOOL_CALL_END"

    // Multi-Agent (ADR-002)
    StreamMessageTypePlanStart       = "PLAN_START"
    StreamMessageTypePlanStream      = "PLAN_STREAM"
    StreamMessageTypePlanComplete    = "PLAN_COMPLETE"
    StreamMessageTypeSubAgentStart   = "SUB_AGENT_START"
    StreamMessageTypeSubAgentStream  = "SUB_AGENT_STREAM"
    StreamMessageTypeSubAgentEnd     = "SUB_AGENT_END"
    StreamMessageTypeSynthesisStart  = "SYNTHESIS_START"
    StreamMessageTypeSynthesisStream = "SYNTHESIS_STREAM"
)
```

### 4.2 Mapping pro Agent-Typ

| Agent-Typ | Reasoning-Quelle | Tool-Call-Quelle |
|-----------|-------------------|------------------|
| **Foundry** | Response-API: `reasoning` Content-Part (wenn verfügbar; aktuell nicht gesendet) | `response.output_item.added` mit `workflow_action` → muss erweitert werden um Input/Output zu capturen |
| **Custom/LangChain** | SDK `StreamWriter` — Agent emittiert explizit | SDK `StreamWriter` — Agent emittiert explizit; oder automatisch via Tracer-Callbacks |
| **N8N** | Nicht unterstützt (N8N streamt keine Reasoning-Tokens) | N8N Webhook-Payload → Agent-Service parst Tool-Node-Ausführungen |
| **OpenAI Direct** | `choices[].delta.reasoning_content` (o1/o3 models) | `choices[].delta.tool_calls[]` — function name + arguments streamed |

### 4.3 Foundry-Erweiterung

Aktueller Code in `processEvent()` — `workflow_action` Items werden nur als Metadata erfasst:

```go
// AKTUELL: Nur Metadata
case "workflow_action":
    metadata["action_id"] = item.ActionID
    metadata["kind"] = item.Kind
    metadata["status"] = item.Status
```

**Erweiterung:**

```go
// NEU: Vollständige Tool-Call Events
case "workflow_action":
    if item.Status == "in_progress" {
        writer.WriteStreamMessage(StreamMessage{
            Type: StreamMessageTypeToolCallStart,
            Config: map[string]any{
                "tool_call_id":   item.ActionID,
                "tool_name":      item.FunctionName,
                "tool_arguments": item.Arguments,
            },
        })
    } else if item.Status == "completed" {
        writer.WriteStreamMessage(StreamMessage{
            Type: StreamMessageTypeToolCallEnd,
            Config: map[string]any{
                "tool_call_id":    item.ActionID,
                "tool_name":       item.FunctionName,
                "tool_status":     "success",
                "tool_result":     item.Output,
                "tool_duration_ms": item.DurationMs,
            },
        })
    }
```

> **Offener Punkt:** Foundry Response-API v2 liefert aktuell `FunctionName`, `Arguments`, und `Output` NICHT im `workflow_action` Item. Das muss in der Foundry-Client-Integration ergänzt werden (ggf. via separatem API-Call oder erweitertem Event-Payload).

---

## 5. Frontend-Implementierung (React/TypeScript)

### 5.1 Erweiterte TypeScript-Types

```typescript
// api/types.ts
type StreamMessageType =
  | "STREAM_START"
  | "TEXT_STREAM"
  | "STREAM_NEW_MESSAGE"
  | "STREAM_END"
  | "MESSAGE_COMPLETE"
  | "TITLE_GENERATION"
  | "ERROR"
  // NEU
  | "REASONING_START"
  | "REASONING_STREAM"
  | "REASONING_END"
  | "TOOL_CALL_START"
  | "TOOL_CALL_STREAM"
  | "TOOL_CALL_END"
  // Multi-Agent (ADR-002)
  | "PLAN_START"
  | "PLAN_STREAM"
  | "PLAN_COMPLETE"
  | "SUB_AGENT_START"
  | "SUB_AGENT_STREAM"
  | "SUB_AGENT_END"
  | "SYNTHESIS_START"
  | "SYNTHESIS_STREAM";

interface ToolCallState {
  toolCallId: string;
  toolName: string;
  toolArguments: Record<string, any>;
  toolStatus: "running" | "success" | "error";
  toolResult?: string;
  toolError?: string;
  toolDurationMs?: number;
}
```

### 5.2 Neuer State in `useChat`

```typescript
// hooks/chat/useChat.ts
const [isReasoning, setIsReasoning] = useState(false);
const [reasoningContent, setReasoningContent] = useState("");
const [activeToolCalls, setActiveToolCalls] = useState<ToolCallState[]>([]);
const [completedToolCalls, setCompletedToolCalls] = useState<ToolCallState[]>([]);
```

### 5.3 Callback-Dispatch (erweitert)

```typescript
// In sendMessageStream callback dispatch:
case "REASONING_START":
  setIsReasoning(true);
  setReasoningContent("");
  break;

case "REASONING_STREAM":
  setReasoningContent(prev => prev + message.content);
  break;

case "REASONING_END":
  setIsReasoning(false);
  break;

case "TOOL_CALL_START":
  setActiveToolCalls(prev => [...prev, {
    toolCallId: message.config.tool_call_id,
    toolName: message.config.tool_name,
    toolArguments: message.config.tool_arguments,
    toolStatus: "running",
  }]);
  break;

case "TOOL_CALL_END":
  setActiveToolCalls(prev =>
    prev.filter(tc => tc.toolCallId !== message.config.tool_call_id)
  );
  setCompletedToolCalls(prev => [...prev, {
    toolCallId: message.config.tool_call_id,
    toolName: message.config.tool_name,
    toolArguments: message.config.tool_arguments ?? {},
    toolStatus: message.config.tool_status === "success" ? "success" : "error",
    toolResult: message.config.tool_result,
    toolError: message.config.tool_error,
    toolDurationMs: message.config.tool_duration_ms,
  }]);
  break;
```

### 5.4 UI-Rendering

**Reasoning (Collapsible):**

```
┌─────────────────────────────────────────────────┐
│ 💭 Reasoning  [▼ collapse]                      │
│ ┌─────────────────────────────────────────────┐ │
│ │ Ich muss die Datenbank durchsuchen, weil    │ │
│ │ der User nach Architektur-Dokumenten fragt...│ │
│ │ ▊ (blinking cursor while isReasoning=true)  │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**Tool Calls (Karten):**

```
┌─────────────────────────────────────────────────┐
│ 🔧 search_knowledge_base                        │
│ Status: ✅ success (342ms)                       │
│ ┌─ Arguments ──────────────────────────────────┐│
│ │ query: "unified-ui architecture"             ││
│ │ top_k: 5                                     ││
│ └──────────────────────────────────────────────┘│
│ ┌─ Result ─────────────────────────────────────┐│
│ │ Found 3 documents: [1] Architecture Overview ││
│ │ [2] API Reference, [3] Deployment Guide      ││
│ └──────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ 🔧 fetch_document          ⏳ running...         │
│ ┌─ Arguments ──────────────────────────────────┐│
│ │ doc_id: "arch-overview-001"                  ││
│ └──────────────────────────────────────────────┘│
│ [loading spinner]                               │
└─────────────────────────────────────────────────┘
```

**Gesamtansicht einer Nachricht:**

```
┌─ Assistant Message ─────────────────────────────┐
│                                                  │
│ 💭 Reasoning [▶ expand]                         │
│                                                  │
│ 🔧 search_knowledge_base  ✅ 342ms              │
│ 🔧 fetch_document         ✅ 128ms              │
│                                                  │
│ Basierend auf den Ergebnissen meiner Recherche   │
│ hier die Architektur von unified-ui:             │
│                                                  │
│ 1. **Agent-Service** — Go/Gin Microservice...    │
│ 2. **Platform-Service** — Python/FastAPI...      │
│ ...                                              │
└─────────────────────────────────────────────────┘
```

---

## 6. SDK Streaming-Modul (`unifiedui_sdk.streaming`)

Das Streaming-Modul im SDK liefert Python-Models und einen `StreamWriter`, mit dem Custom-Agents (LangChain/LangGraph) standardisiert streamen können.

### 6.1 Architektur

```
unifiedui_sdk/streaming/
├── __init__.py          # Public API exports
├── models.py            # Pydantic StreamMessage, StreamConfig, Enums
├── writer.py            # StreamWriter — yields StreamMessage-Objekte
└── README.md            # Dokumentation
```

### 6.2 Models

```python
# streaming/models.py
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class StreamMessageType(StrEnum):
    STREAM_START = "STREAM_START"
    TEXT_STREAM = "TEXT_STREAM"
    STREAM_NEW_MESSAGE = "STREAM_NEW_MESSAGE"
    STREAM_END = "STREAM_END"
    MESSAGE_COMPLETE = "MESSAGE_COMPLETE"
    TITLE_GENERATION = "TITLE_GENERATION"
    ERROR = "ERROR"
    REASONING_START = "REASONING_START"
    REASONING_STREAM = "REASONING_STREAM"
    REASONING_END = "REASONING_END"
    TOOL_CALL_START = "TOOL_CALL_START"
    TOOL_CALL_STREAM = "TOOL_CALL_STREAM"
    TOOL_CALL_END = "TOOL_CALL_END"
    # Multi-Agent (ADR-002)
    PLAN_START = "PLAN_START"
    PLAN_STREAM = "PLAN_STREAM"
    PLAN_COMPLETE = "PLAN_COMPLETE"
    SUB_AGENT_START = "SUB_AGENT_START"
    SUB_AGENT_STREAM = "SUB_AGENT_STREAM"
    SUB_AGENT_END = "SUB_AGENT_END"
    SYNTHESIS_START = "SYNTHESIS_START"
    SYNTHESIS_STREAM = "SYNTHESIS_STREAM"


class StreamMessage(BaseModel):
    type: StreamMessageType
    content: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
```

### 6.3 StreamWriter

```python
# streaming/writer.py
class StreamWriter:
    """Builds and yields StreamMessage objects for unified-ui SSE protocol."""

    async def stream_start(self, config: dict | None = None) -> StreamMessage: ...
    async def text(self, content: str) -> StreamMessage: ...
    async def reasoning_start(self) -> StreamMessage: ...
    async def reasoning(self, content: str) -> StreamMessage: ...
    async def reasoning_end(self) -> StreamMessage: ...
    async def tool_call_start(
        self, tool_call_id: str, tool_name: str, arguments: dict
    ) -> StreamMessage: ...
    async def tool_call_stream(
        self, tool_call_id: str, content: str
    ) -> StreamMessage: ...
    async def tool_call_end(
        self, tool_call_id: str, tool_name: str,
        status: str, result: str | None = None,
        error: str | None = None, duration_ms: int | None = None,
    ) -> StreamMessage: ...
    # Multi-Agent (ADR-002)
    async def plan_start(self) -> StreamMessage: ...
    async def plan_stream(self, content: str) -> StreamMessage: ...
    async def plan_complete(self, plan: dict) -> StreamMessage: ...
    async def sub_agent_start(
        self, sub_agent_id: str, name: str, step: int, tools: list[str]
    ) -> StreamMessage: ...
    async def sub_agent_stream(
        self, sub_agent_id: str, content: str
    ) -> StreamMessage: ...
    async def sub_agent_end(
        self, sub_agent_id: str, name: str, status: str,
        result_summary: str, duration_ms: int | None = None,
    ) -> StreamMessage: ...
    async def synthesis_start(self) -> StreamMessage: ...
    async def synthesis_stream(self, content: str) -> StreamMessage: ...
    async def stream_end(self) -> StreamMessage: ...
    async def message_complete(self, message: dict) -> StreamMessage: ...
```

**Nutzung in einem Custom Agent (FastAPI/Starlette):**

```python
from starlette.responses import StreamingResponse
from unifiedui_sdk.streaming import StreamWriter

async def agent_endpoint(request: Request):
    writer = StreamWriter()

    async def generate():
        yield (await writer.stream_start()).model_dump_json()

        # Reasoning
        yield (await writer.reasoning_start()).model_dump_json()
        yield (await writer.reasoning("Analyzing the query...")).model_dump_json()
        yield (await writer.reasoning_end()).model_dump_json()

        # Tool call
        yield (await writer.tool_call_start("tc_1", "search_db", {"q": "test"})).model_dump_json()
        result = await search_db(q="test")
        yield (await writer.tool_call_end("tc_1", "search_db", "success", result)).model_dump_json()

        # Final answer
        async for token in llm.astream("..."):
            yield (await writer.text(token)).model_dump_json()

        yield (await writer.stream_end()).model_dump_json()

    return StreamingResponse(generate(), media_type="text/event-stream")
```

### 6.4 Integration mit Tracer (Zukunft)

Der bestehende `BaseTracer` fängt bereits `on_tool_start` / `on_tool_end` Callbacks ab. Eine zukünftige Integration könnte den Tracer mit einem `StreamWriter` koppeln:

```python
tracer = UnifiedUILangchainTracer(stream_writer=writer)
# Tracer emittiert automatisch TOOL_CALL_START/END events
# basierend auf den LangChain Callbacks
```

Dies ermöglicht **Zero-Config Tool-Call-Streaming** für LangChain/LangGraph-Agents.

---

## 7. Mapping: Agent-Typ → Stream-Events

| Event | Foundry | OpenAI Direct | LangChain/SDK | N8N |
|-------|---------|---------------|---------------|-----|
| `REASONING_*` | ❌ Nicht verfügbar¹ | ✅ `reasoning_content` delta | ✅ Via StreamWriter | ❌ |
| `TOOL_CALL_*` | ⚠️ `workflow_action` (erweitern)² | ✅ `tool_calls` delta | ✅ Via StreamWriter / Tracer | ⚠️ Via Webhook-Payload |
| `TEXT_STREAM` | ✅ `response.output_text.delta` | ✅ `content` delta | ✅ Via StreamWriter | ✅ Finale Antwort |
| `PLAN_*` | ❌ | ❌ | ✅ ReACT Agent Engine (ADR-002) | ❌ |
| `SUB_AGENT_*` | ❌ | ❌ | ✅ ReACT Agent Engine (ADR-002) | ❌ |
| `SYNTHESIS_*` | ❌ | ❌ | ✅ ReACT Agent Engine (ADR-002) | ❌ |

¹ Foundry Response-API liefert aktuell keine Reasoning-Tokens. Muss beobachtet werden — Azure könnte das in zukünftigen API-Versionen ergänzen.

² Foundry `workflow_action` Items enthalten aktuell nur `action_id`, `kind`, `status`. `FunctionName`, `Arguments`, `Output` müssen aus dem erweiterten Event-Payload oder via separatem API-Call gelesen werden.

---

## 8. Backward-Compatibility

| Aspekt | Garantie |
|--------|----------|
| Bestehende StreamMessage-Struktur | ✅ `{type, content, config}` bleibt unverändert |
| Bestehende 7 Typen | ✅ Verhalten identisch, keine Breaking Changes |
| Frontend ohne Update | ✅ Ignoriert unbekannte Typen — `default: break` im Switch |
| Agents ohne Reasoning/Tools | ✅ Senden weiterhin nur `TEXT_STREAM` — kein Zwang |
| SSE Wire-Format | ✅ `event: message\ndata: {...}\n\n` bleibt gleich |

### Rollout-Strategie

1. Agent-Service: Neue Typen hinzufügen, Foundry-Client erweitern
2. Frontend: Neue Callbacks + UI-Komponenten (Reasoning-Collapsible, Tool-Call-Karten)
3. SDK: `streaming` Modul mit Models + StreamWriter
4. Schrittweise Aktivierung pro Agent-Typ

---

## 9. Offene Fragen / Diskussionspunkte

| # | Frage | Optionen |
|---|-------|----------|
| 1 | **TOOL_CALL_STREAM nötig?** | (A) Ja — für große Tool-Ergebnisse (z.B. Dokument-Inhalte) im Stream. (B) Nein — `TOOL_CALL_END` liefert das Ergebnis komplett. Einfacher, weniger State. |
| 2 | **Reasoning standardmäßig collapsed?** | (A) Collapsed — User muss expandieren. Weniger visuelles Rauschen. (B) Expanded — User sieht Reasoning direkt. Transparenter. |
| 3 | **Tool-Call-Argumente anzeigen?** | (A) Immer anzeigen. (B) Nur auf Klick (Privacy/PII-Bedenken bei Argumenten). (C) Konfigurierbar per Tenant-Setting. |
| 4 | **Foundry Reasoning-Gap** | Warten auf Azure API-Update oder eigene Reasoning-Heuristik basierend auf Model-Typ? |
| 5 | **MESSAGE_COMPLETE erweitern?** | Sollen Reasoning + Tool-Calls auch in der finalen `MESSAGE_COMPLETE` Nachricht als Metadaten enthalten sein? (Für History-Replay ohne Re-Streaming) |
| 6 | **Persistierung** | Tool-Calls und Reasoning als Teil der Message in der DB speichern? Eigenständige Tabelle/Collection? Nur als Trace-Nodes? |
| 7 | **REASONING_START/END vs. nur REASONING_STREAM?** | START/END ermöglicht präziseres State-Management (Loading-Animation), erhöht aber Protokoll-Komplexität. Alternative: Nur `REASONING_STREAM` und Frontend inferiert Start/Ende aus Vorhandensein. |

---

## 10. Zusammenfassung

```
Erweiterte SSE-Architektur:

Single-Agent:
  STREAM_START ─┬─ REASONING_START ─── REASONING_STREAM* ─── REASONING_END
                ├─ TOOL_CALL_START ─── (TOOL_CALL_STREAM*) ── TOOL_CALL_END
                ├─ TOOL_CALL_START ─── (TOOL_CALL_STREAM*) ── TOOL_CALL_END
                ├─ TEXT_STREAM*
                ├─ STREAM_END
                └─ MESSAGE_COMPLETE

Multi-Agent (ADR-002):
  STREAM_START ─┬─ PLAN_START ─── PLAN_STREAM* ─── PLAN_COMPLETE
                ├─ SUB_AGENT_START ─┬─ TOOL_CALL_START/END ── SUB_AGENT_STREAM* ── SUB_AGENT_END
                │                   └─ (parallel: weitere SUB_AGENT_START...END)
                ├─ SUB_AGENT_START ─── ... ─── SUB_AGENT_END  (nächster Step)
                ├─ SYNTHESIS_START ─── SYNTHESIS_STREAM*
                ├─ STREAM_END
                └─ MESSAGE_COMPLETE

14 neue Event-Typen (6 Single + 8 Multi), 0 Breaking Changes, 3 Layer
```
