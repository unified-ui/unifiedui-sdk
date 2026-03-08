# ADR-002: ReACT Agent Engine — LangChain/LangGraph

**Status:** Draft
**Datum:** 2026-03-07
**Autor:** Enrico Goerlitz
**Abhängigkeit:** [ADR-001: Streaming-Konzept](001_STREAMING_CONCEPT.md) (erweitert um Multi-Agent-Events)

---

## 1. Motivation

Aktuell unterstützt unified-ui externe Agent-Backends (N8N, Microsoft Foundry). Diese erfordern externe Infrastruktur und bieten eingeschränkte Kontrolle über Reasoning, Tool-Ausführung und Streaming-Granularität.

Ziel ist eine **native ReACT Agent Engine** im SDK (`unifiedui_sdk.agents`), die:

- Direkt im Agent-Service (als Custom-Agent-Typ) oder standalone läuft
- Auf LangChain/LangGraph aufbaut
- System Instructions, Tools (OpenAPI + MCP), Security/Response-Prompts unterstützt
- Ein **Multi-Agent-System** mit dynamischer Orchestrierung ermöglicht
- Alles in Echtzeit streamt: Planung, Reasoning, Tool-Calls, Sub-Agent-Aktivität

---

## 2. Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Agent-Service (Go)                           │
│                                                                     │
│   AgentType: REACT_AGENT (neu)                                      │
│                                                                     │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │  platformClient.GetReActAgentConfig(tenantID, agentID)    │     │
│   │  → ReActAgentConfig (prompts, tool_ids, ai_model_ids,     │     │
│   │    config.multi_agent_enabled, ...)                        │     │
│   └────────────────────────┬──────────────────────────────────┘     │
│                            │                                         │
│                            ▼                                         │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │  reactAgentWorkflowAdapter                                 │     │
│   │  → POST {sdkEndpoint}/invoke-stream                        │     │
│   │  → SSE StreamReader                                        │     │
│   └────────────────────────┬──────────────────────────────────┘     │
│                            │                                         │
│                            ▼                                         │
│   handleReActStreaming() → SSE Writer → Client                      │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             │ HTTP POST + SSE Stream
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  SDK Agent Engine (Python)                           │
│                  unifiedui_sdk.agents                                │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │  ReActAgentEngine                                        │       │
│   │  ├── config: ReActAgentConfig                            │       │
│   │  ├── llm: ChatModel (LangChain)                         │       │
│   │  ├── tools: list[BaseTool] (OpenAPI + MCP)               │       │
│   │  ├── tracer: UnifiedUILangchainTracer                    │       │
│   │  ├── stream_writer: StreamWriter                         │       │
│   │  │                                                       │       │
│   │  │  multi_agent_enabled = false:                         │       │
│   │  │  └── SingleAgentExecutor (LangGraph ReACT)            │       │
│   │  │                                                       │       │
│   │  │  multi_agent_enabled = true:                          │       │
│   │  │  └── OrchestratorAgent                                │       │
│   │  │      ├── PlannerNode → ExecutionPlan                  │       │
│   │  │      ├── ExecutorNode → SubAgent-Pool                 │       │
│   │  │      │   ├── Step 1: [SubAgent-A ∥ SubAgent-B]        │       │
│   │  │      │   ├── Step 2: [SubAgent-C]                     │       │
│   │  │      │   └── Step 3: [SubAgent-D ∥ SubAgent-E]        │       │
│   │  │      └── SynthesizerNode → Final Response             │       │
│   │  └──────────────────────────────────────────────────────┘       │
│                                                                     │
│   Tool Loading:                                                     │
│   ├── OpenAPI → openapi_to_langchain_tools(spec, credential)        │
│   └── MCP    → mcp_to_langchain_tools(server_config, credential)    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. ReACT Agent Konfiguration

### 3.1 Aktuelles Frontend-Modell (ReActAgentDeveloperPage)

| Feld | Typ | Beschreibung |
|------|-----|-------------|
| `name` | `string` | Agent-Name |
| `description` | `string?` | Beschreibung |
| `ai_model_ids` | `string[]` | AI-Modelle (Purpose: `REACT_AGENT`) |
| `system_prompt` | `string?` | System Instructions (max 8000) |
| `tool_ids` | `string[]` | Tool-IDs (MCP_SERVER / OPENAPI_DEFINITION) |
| `security_prompt` | `string?` | Security-Guardrails (max 8000) |
| `tool_use_prompt` | `string?` | Tool-Use-Anweisungen (max 8000) |
| `response_prompt` | `string?` | Response-Format-Anweisungen (max 8000) |
| `greeting_messages` | `string[]` | Begrüßungsnachrichten |
| `config` | `dict` | Freiform-JSON für Erweiterungen |
| `is_active` | `bool` | Aktiv/Inaktiv-Toggle |

### 3.2 Erweiterung: `config`-Feld für Multi-Agent

Das `config`-Feld (freiform `dict` / `Record<string, unknown>`) wird strukturiert genutzt:

```json
{
  "multi_agent_enabled": false,
  "max_iterations": 15,
  "max_execution_time_seconds": 120,
  "temperature": 0.1,
  "parallel_tool_calls": true,
  "multi_agent": {
    "max_sub_agents": 5,
    "max_parallel_per_step": 3,
    "max_planning_iterations": 2,
    "sub_agent_max_iterations": 10,
    "sub_agent_max_execution_time_seconds": 60,
    "planning_model_id": null
  }
}
```

### 3.3 Frontend-Erweiterung (ReActAgentDeveloperPage)

Neuer Accordion-Bereich **"Agent Engine"** mit:

```
┌─ Agent Engine ──────────────────────────────────────────────┐
│                                                              │
│  Max Iterations        [  15  ]                              │
│  Max Execution Time    [ 120s ]                              │
│  Temperature           [ 0.1  ]                              │
│  Parallel Tool Calls   [✓]                                   │
│                                                              │
│  ─── Multi-Agent ──────────────────────────────────────────  │
│                                                              │
│  Enable Multi-Agent    [ Toggle ]                            │
│                                                              │
│  (wenn enabled:)                                             │
│  Max Sub-Agents            [ 5 ]                             │
│  Max Parallel per Step     [ 3 ]                             │
│  Max Planning Iterations   [ 2 ]                             │
│  Sub-Agent Max Iterations  [ 10 ]                            │
│  Sub-Agent Max Exec Time   [ 60s ]                           │
│  Planning Model            [ Select / default: same ]        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Tool-Integration

### 4.1 Tool-Typen

| Typ | Quelle | Verarbeitung |
|-----|--------|-------------|
| `OPENAPI_DEFINITION` | OpenAPI 3.x Spec (JSON/YAML) in `tool.config` | Wird zur Laufzeit in LangChain-`BaseTool`s konvertiert. Jede Operation → ein Tool. |
| `MCP_SERVER` | MCP Server Konfiguration in `tool.config` | Wird via MCP-Client zur Laufzeit verbunden. Jedes MCP-Tool → ein LangChain-`BaseTool`. |

### 4.2 OpenAPI Tool Config

```json
{
  "type": "OPENAPI_DEFINITION",
  "config": {
    "spec_url": "https://api.example.com/openapi.json",
    "spec_inline": null,
    "base_url": "https://api.example.com",
    "auth_type": "bearer",
    "selected_operations": ["searchDocuments", "getDocument"],
    "timeout_seconds": 30
  }
}
```

**Konvertierung:**

```python
# SDK: tools/openapi.py
def openapi_to_langchain_tools(
    spec: dict | str,
    base_url: str,
    credential: str | None = None,
    selected_operations: list[str] | None = None,
    timeout: int = 30,
) -> list[BaseTool]:
    """Parst OpenAPI-Spec und erzeugt je Operation ein LangChain-Tool.

    Jedes Tool hat:
    - name: operationId
    - description: summary + description aus der Spec
    - args_schema: Pydantic-Model generiert aus parameters + requestBody
    - _run(): HTTP-Request an base_url + path
    """
```

### 4.3 MCP Tool Config

```json
{
  "type": "MCP_SERVER",
  "config": {
    "transport": "sse",
    "url": "https://mcp.example.com/sse",
    "headers": {}
  }
}
```

Alternativ (stdio):

```json
{
  "type": "MCP_SERVER",
  "config": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/data"]
  }
}
```

**Konvertierung:**

```python
# SDK: tools/mcp.py
async def mcp_to_langchain_tools(
    config: dict,
    credential: str | None = None,
) -> list[BaseTool]:
    """Verbindet sich mit MCP-Server, listet Tools, und erzeugt LangChain-Tools.

    Nutzt das MCP Python SDK (mcp) für:
    - SSE-Transport: mcp.client.sse.sse_client()
    - Stdio-Transport: mcp.client.stdio.stdio_client()

    Jedes MCP-Tool wird in ein LangChain-BaseTool gewrappt:
    - name: mcp_tool.name
    - description: mcp_tool.description
    - args_schema: generiert aus mcp_tool.inputSchema
    - _run(): ruft mcp_client.call_tool() auf
    """
```

### 4.4 Tool-Laden zur Laufzeit

```python
async def load_tools(
    tool_configs: list[ToolConfig],
    credentials: dict[str, str],
) -> list[BaseTool]:
    """Lädt alle Tools parallel basierend auf ihrem Typ."""
    tasks = []
    for tool_cfg in tool_configs:
        cred = credentials.get(tool_cfg.credential_id)
        if tool_cfg.type == ToolType.OPENAPI_DEFINITION:
            tasks.append(openapi_to_langchain_tools(tool_cfg.config, cred))
        elif tool_cfg.type == ToolType.MCP_SERVER:
            tasks.append(mcp_to_langchain_tools(tool_cfg.config, cred))
    results = await asyncio.gather(*tasks)
    return [tool for tools in results for tool in tools]
```

---

## 5. Single-Agent Modus

### 5.1 LangGraph ReACT Graph

Wenn `multi_agent_enabled = false`, wird ein Standard-LangGraph-ReACT-Agent erstellt:

```
                    ┌─────────┐
                    │  START   │
                    └────┬────┘
                         ▼
                    ┌─────────┐
              ┌────►│  Agent  │◄────┐
              │     └────┬────┘     │
              │          │          │
              │     tool_calls?     │
              │     /         \     │
              │   yes          no   │
              │   │             │   │
              │   ▼             ▼   │
              │ ┌───────┐  ┌──────┐│
              └─┤ Tools  │  │ END  ││
                └───────┘  └──────┘│
```

```python
from langgraph.prebuilt import create_react_agent

graph = create_react_agent(
    model=llm,
    tools=tools,
    prompt=system_message,
    max_iterations=config.max_iterations,
)
```

### 5.2 Prompt-Assembly

Die verschiedenen Prompt-Felder werden zu einem System-Prompt zusammengeführt:

```python
def build_system_prompt(config: ReActAgentConfig) -> str:
    sections = []
    if config.system_prompt:
        sections.append(f"<instructions>\n{config.system_prompt}\n</instructions>")
    if config.security_prompt:
        sections.append(f"<security>\n{config.security_prompt}\n</security>")
    if config.tool_use_prompt:
        sections.append(f"<tool_use>\n{config.tool_use_prompt}\n</tool_use>")
    if config.response_prompt:
        sections.append(f"<response_format>\n{config.response_prompt}\n</response_format>")
    return "\n\n".join(sections)
```

### 5.3 Streaming (Single-Agent)

```python
async def invoke_stream(self, message: str, history: list) -> AsyncGenerator[StreamMessage]:
    writer = StreamWriter()
    yield writer.stream_start()

    async for event in graph.astream_events(input, version="v2"):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            # Reasoning (wenn supported)
            if hasattr(chunk, "reasoning_content") and chunk.reasoning_content:
                if not reasoning_started:
                    yield writer.reasoning_start()
                    reasoning_started = True
                yield writer.reasoning(chunk.reasoning_content)
            # Content
            elif chunk.content:
                if reasoning_started:
                    yield writer.reasoning_end()
                    reasoning_started = False
                yield writer.text(chunk.content)

        elif kind == "on_tool_start":
            yield writer.tool_call_start(
                tool_call_id=event["run_id"],
                tool_name=event["name"],
                arguments=event["data"].get("input", {}),
            )

        elif kind == "on_tool_end":
            yield writer.tool_call_end(
                tool_call_id=event["run_id"],
                tool_name=event["name"],
                status="success",
                result=str(event["data"].get("output", "")),
            )

    yield writer.stream_end()
    yield writer.message_complete(...)
```

---

## 6. Multi-Agent Modus

### 6.1 Konzept

Wenn `multi_agent_enabled = true`, erstellt die Engine einen **Orchestrator-Agenten**, der dynamisch Sub-Agenten plant und ausführt.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Orchestrator Graph                            │
│                                                                      │
│   ┌──────────┐     ┌──────────┐     ┌─────────────┐     ┌────────┐ │
│   │ Planner  │────►│ Executor │────►│ Synthesizer │────►│  END   │ │
│   └──────────┘     └──────────┘     └─────────────┘     └────────┘ │
│        │                │                   │                        │
│        │                │                   │                        │
│    Generiert        Führt Plan          Kombiniert                   │
│    ExecutionPlan    aus (seq +          Sub-Agent-                   │
│    mit Steps +      parallel)          Ergebnisse                   │
│    Sub-Agents                          zur finalen                  │
│                                        Antwort                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 ExecutionPlan-Modell

Der Planner-Agent generiert einen strukturierten Plan:

```python
class SubAgentTask(BaseModel):
    """Einzelne Sub-Agent-Aufgabe."""
    id: str                              # z.B. "task_1"
    name: str                            # z.B. "Recherche-Agent"
    description: str                     # Was soll der Sub-Agent tun?
    instructions: str                    # Spezifische Anweisungen
    required_tool_names: list[str]       # Welche Tools braucht der Sub-Agent?
    depends_on: list[str]               # Task-IDs, von denen dieses Task abhängt

class ExecutionStep(BaseModel):
    """Gruppe von parallel ausführbaren Tasks."""
    step_number: int
    tasks: list[SubAgentTask]

class ExecutionPlan(BaseModel):
    """Vom Planner generierter Ausführungsplan."""
    goal: str                            # Zusammenfassung des Ziels
    reasoning: str                       # Warum dieser Plan?
    steps: list[ExecutionStep]           # Sequentielle Steps mit parallelen Tasks
    estimated_complexity: str            # "simple" | "moderate" | "complex"
```

**Beispiel:**

User: *"Recherchiere die Architektur von unified-ui und erstelle eine Zusammenfassung. Übersetze sie dann ins Deutsche."*

```json
{
  "goal": "Recherche + Zusammenfassung + Übersetzung",
  "reasoning": "Drei Teilaufgaben: (1) Recherche und (2) Zusammenfassung können nicht parallel laufen (2 hängt von 1 ab). (3) Übersetzung hängt von 2 ab.",
  "steps": [
    {
      "step_number": 1,
      "tasks": [
        {
          "id": "task_1",
          "name": "Recherche-Agent",
          "description": "Durchsuche die Knowledge Base nach unified-ui Architektur-Dokumenten",
          "instructions": "Nutze search_knowledge_base um alle relevanten Architektur-Dokumente zu finden. Gib die vollständigen Inhalte zurück.",
          "required_tool_names": ["search_knowledge_base", "fetch_document"],
          "depends_on": []
        }
      ]
    },
    {
      "step_number": 2,
      "tasks": [
        {
          "id": "task_2",
          "name": "Zusammenfassungs-Agent",
          "description": "Erstelle eine strukturierte Zusammenfassung der Architektur",
          "instructions": "Fasse die Recherche-Ergebnisse aus task_1 zu einer klaren, strukturierten Architektur-Übersicht zusammen.",
          "required_tool_names": [],
          "depends_on": ["task_1"]
        }
      ]
    },
    {
      "step_number": 3,
      "tasks": [
        {
          "id": "task_3",
          "name": "Übersetzungs-Agent",
          "description": "Übersetze die Zusammenfassung ins Deutsche",
          "instructions": "Übersetze die Zusammenfassung aus task_2 ins Deutsche. Behalte die Markdown-Struktur bei.",
          "required_tool_names": [],
          "depends_on": ["task_2"]
        }
      ]
    }
  ],
  "estimated_complexity": "moderate"
}
```

**Beispiel mit Parallelität:**

User: *"Finde die aktuellen Wetterdaten für Berlin, München und Hamburg und erstelle einen Vergleich."*

```json
{
  "goal": "Parallele Wetter-Recherche + Vergleich",
  "reasoning": "Die drei Städte-Abfragen sind unabhängig → parallel. Der Vergleich hängt von allen drei ab → sequentiell danach.",
  "steps": [
    {
      "step_number": 1,
      "tasks": [
        {
          "id": "task_1",
          "name": "Wetter-Agent Berlin",
          "description": "Aktuelle Wetterdaten für Berlin abrufen",
          "instructions": "Rufe die aktuellen Wetterdaten für Berlin ab.",
          "required_tool_names": ["get_weather"],
          "depends_on": []
        },
        {
          "id": "task_2",
          "name": "Wetter-Agent München",
          "description": "Aktuelle Wetterdaten für München abrufen",
          "instructions": "Rufe die aktuellen Wetterdaten für München ab.",
          "required_tool_names": ["get_weather"],
          "depends_on": []
        },
        {
          "id": "task_3",
          "name": "Wetter-Agent Hamburg",
          "description": "Aktuelle Wetterdaten für Hamburg abrufen",
          "instructions": "Rufe die aktuellen Wetterdaten für Hamburg ab.",
          "required_tool_names": ["get_weather"],
          "depends_on": []
        }
      ]
    },
    {
      "step_number": 2,
      "tasks": [
        {
          "id": "task_4",
          "name": "Vergleichs-Agent",
          "description": "Erstelle einen Wetter-Vergleich der drei Städte",
          "instructions": "Vergleiche die Ergebnisse von task_1, task_2 und task_3 in einer übersichtlichen Tabelle.",
          "required_tool_names": [],
          "depends_on": ["task_1", "task_2", "task_3"]
        }
      ]
    }
  ],
  "estimated_complexity": "simple"
}
```

### 6.3 Orchestrator LangGraph

```python
from langgraph.graph import StateGraph, START, END

class OrchestratorState(TypedDict):
    messages: Annotated[list, add_messages]
    plan: ExecutionPlan | None
    step_results: dict[str, str]          # task_id → result
    current_step: int
    final_response: str | None

def build_orchestrator_graph(
    llm: BaseChatModel,
    tools: list[BaseTool],
    config: ReActAgentConfig,
) -> CompiledGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        should_continue_or_synthesize,
        {"continue": "executor", "synthesize": "synthesizer"},
    )
    graph.add_edge("synthesizer", END)

    return graph.compile()
```

### 6.4 Planner Node

```python
async def planner_node(state: OrchestratorState, config) -> dict:
    """Generiert einen ExecutionPlan via Structured Output."""
    llm = config["configurable"]["llm"]
    tool_descriptions = config["configurable"]["tool_descriptions"]

    planner_prompt = f"""Du bist ein Aufgaben-Planer. Analysiere die Anfrage des Users
und erstelle einen ExecutionPlan.

Verfügbare Tools:
{tool_descriptions}

Regeln:
- Teile komplexe Aufgaben in unabhängige Sub-Tasks auf
- Tasks ohne Abhängigkeiten kommen in denselben Step (→ parallel)
- Tasks mit Abhängigkeiten kommen in spätere Steps (→ sequentiell)
- Jeder Sub-Agent bekommt nur die Tools, die er braucht
- Einfache Anfragen brauchen keinen Multi-Agent-Plan → 1 Step, 1 Task
"""

    structured_llm = llm.with_structured_output(ExecutionPlan)
    plan = await structured_llm.ainvoke([
        SystemMessage(content=planner_prompt),
        *state["messages"],
    ])

    return {"plan": plan, "current_step": 0, "step_results": {}}
```

### 6.5 Executor Node

```python
async def executor_node(state: OrchestratorState, config) -> dict:
    """Führt den aktuellen Step aus — parallele Sub-Agents."""
    plan = state["plan"]
    step = plan.steps[state["current_step"]]
    llm = config["configurable"]["llm"]
    all_tools = config["configurable"]["tools"]
    stream_writer = config["configurable"]["stream_writer"]

    # Sub-Agents für diesen Step erstellen
    async def run_sub_agent(task: SubAgentTask) -> tuple[str, str]:
        # Tools filtern
        task_tools = [t for t in all_tools if t.name in task.required_tool_names]

        # Kontext aus vorherigen Tasks einsammeln
        context_parts = []
        for dep_id in task.depends_on:
            if dep_id in state["step_results"]:
                context_parts.append(
                    f"<result task_id='{dep_id}'>\n{state['step_results'][dep_id]}\n</result>"
                )

        sub_prompt = f"""{task.instructions}

{'Kontext aus vorherigen Tasks:' + chr(10) + chr(10).join(context_parts) if context_parts else ''}"""

        # Sub-Agent als eigenen ReACT-Graph
        sub_graph = create_react_agent(
            model=llm,
            tools=task_tools,
            prompt=sub_prompt,
        )

        result_parts = []
        async for event in sub_graph.astream_events(
            {"messages": [HumanMessage(content=task.description)]},
            version="v2",
        ):
            # Stream-Events an den Writer weiterleiten
            # (mit sub_agent_id annotiert)
            ...
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if chunk.content:
                    result_parts.append(chunk.content)

        return task.id, "".join(result_parts)

    # Alle Tasks in diesem Step parallel ausführen
    results = await asyncio.gather(
        *[run_sub_agent(task) for task in step.tasks]
    )

    new_results = dict(results)
    merged_results = {**state["step_results"], **new_results}

    return {
        "step_results": merged_results,
        "current_step": state["current_step"] + 1,
    }
```

### 6.6 Synthesizer Node

```python
async def synthesizer_node(state: OrchestratorState, config) -> dict:
    """Kombiniert alle Sub-Agent-Ergebnisse zur finalen Antwort."""
    llm = config["configurable"]["llm"]
    plan = state["plan"]

    context = "\n\n".join(
        f"### {task.name} (task_id: {task.id})\n{state['step_results'].get(task.id, 'No result')}"
        for step in plan.steps
        for task in step.tasks
    )

    synthesis_prompt = f"""Du bist ein Synthese-Agent. Kombiniere die Ergebnisse
der Sub-Agenten zu einer kohärenten, vollständigen Antwort.

Ursprüngliche Anfrage:
{state['messages'][0].content}

Plan:
{plan.goal}

Ergebnisse:
{context}

Erstelle eine vollständige, gut strukturierte Antwort."""

    response = await llm.ainvoke([
        SystemMessage(content=synthesis_prompt),
        HumanMessage(content="Erstelle die finale Antwort."),
    ])

    return {"final_response": response.content}
```

---

## 7. Streaming (Multi-Agent)

### 7.1 Neue StreamMessage-Typen (→ Erweiterung ADR-001)

| Neuer Type | Zweck |
|------------|-------|
| `PLAN_START` | Orchestrator beginnt Planung |
| `PLAN_STREAM` | Plan-Reasoning (delta) |
| `PLAN_COMPLETE` | Fertiger ExecutionPlan |
| `SUB_AGENT_START` | Sub-Agent beginnt Ausführung |
| `SUB_AGENT_STREAM` | Sub-Agent Text-Chunk (delta) |
| `SUB_AGENT_END` | Sub-Agent-Ergebnis abgeschlossen |
| `SYNTHESIS_START` | Synthese-Phase beginnt |
| `SYNTHESIS_STREAM` | Synthese Text-Chunk (delta) — finaler Antwort-Stream |

### 7.2 JSON-Payloads

#### PLAN_START

```json
{
  "type": "PLAN_START",
  "content": "",
  "config": {}
}
```

#### PLAN_STREAM

```json
{
  "type": "PLAN_STREAM",
  "content": "Ich analysiere die Anfrage und plane die Ausführung...",
  "config": {}
}
```

#### PLAN_COMPLETE

```json
{
  "type": "PLAN_COMPLETE",
  "content": "",
  "config": {
    "plan": {
      "goal": "Parallele Wetter-Recherche + Vergleich",
      "reasoning": "Die drei Städte-Abfragen sind unabhängig...",
      "steps": [
        {
          "step_number": 1,
          "tasks": [
            {"id": "task_1", "name": "Wetter-Agent Berlin", "description": "..."},
            {"id": "task_2", "name": "Wetter-Agent München", "description": "..."},
            {"id": "task_3", "name": "Wetter-Agent Hamburg", "description": "..."}
          ]
        },
        {
          "step_number": 2,
          "tasks": [
            {"id": "task_4", "name": "Vergleichs-Agent", "description": "..."}
          ]
        }
      ],
      "estimated_complexity": "simple"
    }
  }
}
```

#### SUB_AGENT_START

```json
{
  "type": "SUB_AGENT_START",
  "content": "",
  "config": {
    "sub_agent_id": "task_1",
    "sub_agent_name": "Wetter-Agent Berlin",
    "step_number": 1,
    "tools": ["get_weather"]
  }
}
```

#### SUB_AGENT_STREAM

```json
{
  "type": "SUB_AGENT_STREAM",
  "content": "Die aktuelle Temperatur in Berlin beträgt...",
  "config": {
    "sub_agent_id": "task_1"
  }
}
```

#### SUB_AGENT_END

```json
{
  "type": "SUB_AGENT_END",
  "content": "",
  "config": {
    "sub_agent_id": "task_1",
    "sub_agent_name": "Wetter-Agent Berlin",
    "status": "success",
    "result_summary": "Berlin: 12°C, bewölkt, 65% Luftfeuchtigkeit",
    "duration_ms": 2340
  }
}
```

#### Tool-Calls innerhalb von Sub-Agents

`TOOL_CALL_START` / `TOOL_CALL_END` aus ADR-001 bekommen ein zusätzliches `sub_agent_id`-Feld:

```json
{
  "type": "TOOL_CALL_START",
  "content": "",
  "config": {
    "tool_call_id": "tc_xyz",
    "tool_name": "get_weather",
    "tool_arguments": {"city": "Berlin"},
    "sub_agent_id": "task_1"
  }
}
```

#### SYNTHESIS_START / SYNTHESIS_STREAM

```json
{
  "type": "SYNTHESIS_START",
  "content": "",
  "config": {}
}
```

```json
{
  "type": "SYNTHESIS_STREAM",
  "content": "Basierend auf den Ergebnissen...",
  "config": {}
}
```

> **Hinweis:** `SYNTHESIS_STREAM` ersetzt `TEXT_STREAM` im Multi-Agent-Modus für die finale Antwort. Das Frontend kann beides identisch rendern — die Unterscheidung ermöglicht die visuelle Zuordnung zur Synthese-Phase.

### 7.3 Vollständiger Multi-Agent Stream-Lifecycle

```
STREAM_START
│
├── PLAN_START
│   ├── PLAN_STREAM  ("Ich analysiere die Anfrage...")
│   ├── PLAN_STREAM  ("...und erstelle einen Ausführungsplan.")
│   └── PLAN_COMPLETE  {plan: ExecutionPlan}
│
├── ── Step 1 (parallel) ────────────────────────────────
│   ├── SUB_AGENT_START         {task_1, "Wetter Berlin"}
│   │   ├── TOOL_CALL_START     {get_weather, Berlin, sub_agent_id: task_1}
│   │   ├── TOOL_CALL_END       {success, "12°C", sub_agent_id: task_1}
│   │   ├── SUB_AGENT_STREAM    ("Berlin: 12°C, bewölkt...")
│   │   └── SUB_AGENT_END       {task_1, success}
│   │
│   ├── SUB_AGENT_START         {task_2, "Wetter München"}  ← parallel
│   │   ├── TOOL_CALL_START     {get_weather, München, sub_agent_id: task_2}
│   │   ├── TOOL_CALL_END       {success, "8°C", sub_agent_id: task_2}
│   │   ├── SUB_AGENT_STREAM    ("München: 8°C, sonnig...")
│   │   └── SUB_AGENT_END       {task_2, success}
│   │
│   └── SUB_AGENT_START         {task_3, "Wetter Hamburg"}  ← parallel
│       ├── TOOL_CALL_START     {get_weather, Hamburg, sub_agent_id: task_3}
│       ├── TOOL_CALL_END       {success, "10°C", sub_agent_id: task_3}
│       ├── SUB_AGENT_STREAM    ("Hamburg: 10°C, Regen...")
│       └── SUB_AGENT_END       {task_3, success}
│
├── ── Step 2 (sequentiell, nach Step 1) ─────────────────
│   └── SUB_AGENT_START         {task_4, "Vergleichs-Agent"}
│       ├── SUB_AGENT_STREAM    ("Vergleich der drei Städte...")
│       └── SUB_AGENT_END       {task_4, success}
│
├── SYNTHESIS_START
│   ├── SYNTHESIS_STREAM  ("Hier ist der Wetter-Vergleich:")
│   ├── SYNTHESIS_STREAM  ("| Stadt | Temp | Wetter |...")
│   └── (SYNTHESIS endet implizit mit STREAM_END)
│
├── STREAM_END
└── MESSAGE_COMPLETE
```

### 7.4 Frontend UI — Multi-Agent-Ansicht

```
┌─ Assistant Message ─────────────────────────────────────────────┐
│                                                                  │
│ 📋 Plan: "Parallele Wetter-Recherche + Vergleich"  [▶ expand]   │
│                                                                  │
│ ── Step 1 ──────────────────────────────────────────────────────│
│                                                                  │
│ 🤖 Wetter-Agent Berlin        ✅ 2340ms                         │
│    🔧 get_weather → "12°C, bewölkt"                             │
│                                                                  │
│ 🤖 Wetter-Agent München       ✅ 1890ms                         │
│    🔧 get_weather → "8°C, sonnig"                               │
│                                                                  │
│ 🤖 Wetter-Agent Hamburg       ✅ 2100ms                         │
│    🔧 get_weather → "10°C, Regen"                               │
│                                                                  │
│ ── Step 2 ──────────────────────────────────────────────────────│
│                                                                  │
│ 🤖 Vergleichs-Agent           ✅ 3200ms                         │
│                                                                  │
│ ────────────────────────────────────────────────────────────────│
│                                                                  │
│ Hier ist der Wetter-Vergleich:                                   │
│                                                                  │
│ | Stadt   | Temperatur | Wetter   | Luftfeuchtigkeit |           │
│ |---------|------------|----------|-----------------|           │
│ | Berlin  | 12°C       | Bewölkt  | 65%             |           │
│ | München | 8°C        | Sonnig   | 45%             |           │
│ | Hamburg | 10°C       | Regen    | 80%             |           │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Live-Streaming-Ansicht (während der Ausführung):**

```
┌─ Assistant Message ─────────────────────────────────────────────┐
│                                                                  │
│ 📋 Plan: "Parallele Wetter-Recherche + Vergleich"               │
│    3 Tasks in 2 Steps · Komplexität: simple                      │
│                                                                  │
│ ── Step 1 (3 parallel) ─────────────────────────────────────────│
│                                                                  │
│ 🤖 Wetter-Agent Berlin        ✅ 2340ms                         │
│    🔧 get_weather → "12°C, bewölkt"                             │
│                                                                  │
│ 🤖 Wetter-Agent München       ⏳ running...                     │
│    🔧 get_weather ⏳                                             │
│                                                                  │
│ 🤖 Wetter-Agent Hamburg       ⏳ running...                     │
│    (waiting for tool result...)                                   │
│                                                                  │
│ ── Step 2 ──────────────────────────────────────────────────────│
│    ⏸️ waiting for Step 1                                         │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. SDK Modul-Struktur

```
unifiedui_sdk/agents/
├── __init__.py                    # Public API: ReActAgentEngine, ReActAgentConfig
├── config.py                      # ReActAgentConfig, MultiAgentConfig (Pydantic)
├── engine.py                      # ReActAgentEngine — Hauptklasse
├── single.py                      # SingleAgentExecutor (LangGraph ReACT)
├── multi/
│   ├── __init__.py
│   ├── orchestrator.py            # OrchestratorGraph (Planner → Executor → Synthesizer)
│   ├── planner.py                 # PlannerNode + ExecutionPlan-Modelle
│   ├── executor.py                # ExecutorNode + parallele Sub-Agent-Ausführung
│   └── synthesizer.py             # SynthesizerNode
├── tools/
│   ├── __init__.py
│   ├── openapi.py                 # openapi_to_langchain_tools()
│   ├── mcp.py                     # mcp_to_langchain_tools()
│   └── loader.py                  # load_tools() — orchestriert Tool-Laden
├── tracing/
│   ├── __init__.py
│   └── tracer.py                  # ReActAgentTracer — erweiterter Tracer
└── README.md
```

### 8.1 ReActAgentEngine (Hauptklasse)

```python
# agents/engine.py
class ReActAgentEngine:
    """Unified ReACT agent engine with optional multi-agent orchestration.

    Args:
        config: Agent configuration from platform service.
        llm: LangChain chat model instance.
        tools: Pre-loaded LangChain tools.
        tracer: Optional UnifiedUI tracer for tracing.
    """

    def __init__(
        self,
        config: ReActAgentConfig,
        llm: BaseChatModel,
        tools: list[BaseTool],
        tracer: BaseTracer | None = None,
    ) -> None:
        self._config = config
        self._llm = llm
        self._tools = tools
        self._tracer = tracer
        self._graph = self._build_graph()

    def _build_graph(self) -> CompiledGraph:
        if self._config.multi_agent_enabled:
            return build_orchestrator_graph(self._llm, self._tools, self._config)
        return build_single_agent_graph(self._llm, self._tools, self._config)

    async def invoke(self, message: str, history: list | None = None) -> str:
        """Synchrone Ausführung — gibt finale Antwort zurück."""
        ...

    async def invoke_stream(
        self, message: str, history: list | None = None
    ) -> AsyncGenerator[StreamMessage, None]:
        """Streaming-Ausführung — yielded StreamMessage-Objekte."""
        ...
```

### 8.2 ReActAgentConfig

```python
# agents/config.py
class MultiAgentConfig(BaseModel):
    max_sub_agents: int = 5
    max_parallel_per_step: int = 3
    max_planning_iterations: int = 2
    sub_agent_max_iterations: int = 10
    sub_agent_max_execution_time_seconds: int = 60
    planning_model_id: str | None = None

class ReActAgentConfig(BaseModel):
    system_prompt: str | None = None
    security_prompt: str | None = None
    tool_use_prompt: str | None = None
    response_prompt: str | None = None
    max_iterations: int = 15
    max_execution_time_seconds: int = 120
    temperature: float = 0.1
    parallel_tool_calls: bool = True
    multi_agent_enabled: bool = False
    multi_agent: MultiAgentConfig = Field(default_factory=MultiAgentConfig)
```

---

## 9. Agent-Service Integration (Go)

### 9.1 Neuer Agent-Typ

```go
// internal/services/platform/models.go
const (
    AgentTypeN8N        AgentType = "N8N"
    AgentTypeFoundry    AgentType = "MICROSOFT_FOUNDRY"
    AgentTypeCopilot    AgentType = "COPILOT"
    AgentTypeCustom     AgentType = "CUSTOM"
    AgentTypeReActAgent AgentType = "REACT_AGENT"   // NEU
)
```

### 9.2 Config-Endpoint (Platform-Service)

Neuer Endpoint im Platform-Service:

```
GET /api/v1/platform-service/tenants/{tenantId}/re-act-agents/{agentId}/config
Header: X-Service-Key, Authorization: Bearer
```

Gibt `ReActAgentConfigResponse` zurück:

```python
class ReActAgentConfigResponse(BaseModel):
    docversion: str = "v1"
    type: str = "REACT_AGENT"
    tenant_id: str
    agent_id: str
    system_prompt: str | None
    security_prompt: str | None
    tool_use_prompt: str | None
    response_prompt: str | None
    config: dict                              # multi_agent_enabled, max_iterations, etc.
    tools: list[ToolWithSecretResponse]        # Aufgelöste Tools mit Credentials
    ai_models: list[AIModelWithSecretResponse]  # Aufgelöste AI-Modelle mit Credentials
    user: UserInfoResponse
```

### 9.3 Flow im Agent-Service

```
POST /tenants/{tenantId}/conversation/messages
    │ chatAgentId → verweist auf ChatAgent mit type=REACT_AGENT
    │              und re_act_agent_id in settings
    ▼
MessagesHandler.SendMessage()
    ├── platformClient.GetAgentConfig()
    │   → type: REACT_AGENT
    │   → settings.re_act_agent_id: "uuid-of-react-agent"
    │   → settings.sdk_endpoint: "https://react-engine.internal:8000"
    │
    ├── agentFactory.CreateReActClients(config)
    │   └── reactWorkflowAdapter
    │       POST {sdkEndpoint}/invoke-stream
    │       Body: { message, history, agent_config }
    │       Response: SSE Stream
    │
    └── handleReActStreaming()
        └── loop: reader.Read() → StreamChunk
            ├── content → writer.WriteTextStream()
            ├── reasoning → writer.WriteReasoningStream()
            ├── tool_call → writer.WriteToolCallStart/End()
            ├── plan → writer.WritePlanComplete()
            ├── sub_agent → writer.WriteSubAgentStart/End()
            ├── synthesis → writer.WriteSynthesisStream()
            └── done → writer.WriteStreamEnd(), save, WriteMessageComplete()
```

### 9.4 SDK als eigenständiger Service

Die Agent Engine wird als eigenständiger Python-Service deployed:

```
┌─────────────────┐       ┌──────────────────────────┐
│  Agent-Service   │ ───── │  SDK Agent Service       │
│  (Go/Gin)        │  SSE  │  (FastAPI/Starlette)     │
│                  │ ◄──── │  unifiedui_sdk.agents     │
└─────────────────┘       └──────────────────────────┘
```

**Endpoint:**

```python
# SDK Service: main.py
@app.post("/invoke-stream")
async def invoke_stream(request: InvokeStreamRequest):
    engine = ReActAgentEngine(
        config=request.agent_config,
        llm=create_llm(request.ai_models),
        tools=await load_tools(request.tools),
    )

    async def generate():
        async for msg in engine.invoke_stream(request.message, request.history):
            yield f"data: {msg.model_dump_json()}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 10. Parallele Ausführung: Streaming-Herausforderung

### Problem

Bei parallelen Sub-Agents kommen Stream-Events **interleaved** an:

```
SUB_AGENT_STREAM {task_1} "Berlin hat..."
SUB_AGENT_STREAM {task_2} "München zeigt..."     ← gleichzeitig
TOOL_CALL_START  {task_3, get_weather}            ← gleichzeitig
SUB_AGENT_STREAM {task_1} "eine Temperatur von..."
TOOL_CALL_END    {task_3, success}                ← gleichzeitig
```

### Lösung

Jedes Event trägt ein `sub_agent_id`-Feld. Das Frontend ordnet Events anhand der `sub_agent_id` dem richtigen Sub-Agent-Container zu:

```typescript
// Frontend State
interface MultiAgentState {
  plan: ExecutionPlan | null;
  subAgents: Map<string, SubAgentState>;
  synthesisContent: string;
}

interface SubAgentState {
  id: string;
  name: string;
  status: "pending" | "running" | "success" | "error";
  content: string;
  toolCalls: ToolCallState[];
  durationMs?: number;
}
```

Der Switch im Frontend dispatcht basierend auf `sub_agent_id`:

```typescript
case "TOOL_CALL_START":
  const subId = message.config.sub_agent_id;
  if (subId) {
    // Tool-Call dem Sub-Agent zuordnen
    updateSubAgent(subId, agent => ({
      ...agent,
      toolCalls: [...agent.toolCalls, { ... }],
    }));
  } else {
    // Single-Agent: wie bisher
    setActiveToolCalls(prev => [...prev, { ... }]);
  }
  break;
```

---

## 11. Sicherheit

### 11.1 Tool-Isolation

- Sub-Agents erhalten **nur die Tools, die im Plan zugewiesen wurden**
- Der Planner kann keine neuen Tools erfinden — nur aus der konfigurierten `tool_ids`-Liste wählen
- Tool-Ausführung wird über den Tracer geloggt (jeder Tool-Call → Trace-Node)

### 11.2 Prompt Injection Defense

- `security_prompt` wird als **System-Level-Guard** in jeden Sub-Agent injected
- Der Planner erhält den `security_prompt` ebenfalls
- Structured Output für den ExecutionPlan reduziert Injection-Risiko (JSON-Schema-Validierung)

### 11.3 Resource Limits

| Limit | Default | Konfigurierbar |
|-------|---------|---------------|
| Max Iterations (Single) | 15 | ✅ `max_iterations` |
| Max Execution Time | 120s | ✅ `max_execution_time_seconds` |
| Max Sub-Agents | 5 | ✅ `multi_agent.max_sub_agents` |
| Max Parallel per Step | 3 | ✅ `multi_agent.max_parallel_per_step` |
| Sub-Agent Max Iterations | 10 | ✅ `multi_agent.sub_agent_max_iterations` |
| Sub-Agent Max Exec Time | 60s | ✅ `multi_agent.sub_agent_max_execution_time_seconds` |

---

## 12. Tracing

Die ReACT Agent Engine benötigt einen **eigenen Tracer**, der über den bestehenden `BaseTracer` (LangChain-Callbacks) hinaus die Multi-Agent-spezifischen Abläufe erfasst.

### 12.1 Anforderungen

Der bestehende `UnifiedUILangchainTracer` / `UnifiedUILanggraphTracer` deckt bereits ab:
- LLM-Calls (`on_llm_start/end`)
- Tool-Calls (`on_tool_start/end`)
- Chain/Agent-Runs (`on_chain_start/end`)
- Retriever-Calls (`on_retriever_start/end`)

Für die ReACT Agent Engine fehlen:

| Aspekt | Was fehlt |
|--------|-----------|
| **Orchestrator-Ebene** | Plan-Generierung als Trace-Node (Planner → ExecutionPlan) |
| **Sub-Agent-Ebene** | Jeder Sub-Agent als eigener Trace-Subtree mit eigenem `parent_run_id` |
| **Parallele Ausführung** | Mehrere gleichzeitige Sub-Agent-Traces korrekt verschachtelt |
| **Synthese** | Synthesizer-LLM-Call als eigener Trace-Node |
| **Plan-Metadaten** | ExecutionPlan als Metadata am Root-Trace |
| **Sub-Agent-Zuordnung** | `sub_agent_id`, `step_number` als Metadata an Trace-Nodes |

### 12.2 ReActAgentTracer

```python
# agents/tracing/tracer.py
class ReActAgentTracer(UnifiedUILanggraphTracer):
    """Extended tracer for ReACT Agent Engine with multi-agent support.

    Extends the base LangGraph tracer with:
    - Orchestrator-level trace nodes (planner, executor, synthesizer)
    - Sub-agent trace subtrees with correct parent-child relationships
    - ExecutionPlan as metadata
    - Parallel sub-agent trace correlation
    """

    def __init__(
        self,
        trace_id: str | None = None,
        conversation_id: str | None = None,
        message_id: str | None = None,
        stream_writer: StreamWriter | None = None,
    ) -> None:
        super().__init__(
            trace_id=trace_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        self._stream_writer = stream_writer
        self._plan: ExecutionPlan | None = None
        self._sub_agent_traces: dict[str, str] = {}  # sub_agent_id → trace_node_id

    def on_plan_created(self, plan: ExecutionPlan) -> None:
        """Erfasst den generierten ExecutionPlan als Trace-Node."""
        node = self._create_trace_node(
            name="Planner",
            node_type=TraceNodeType.AGENT,
            metadata={
                "plan_goal": plan.goal,
                "plan_reasoning": plan.reasoning,
                "total_steps": len(plan.steps),
                "total_tasks": sum(len(s.tasks) for s in plan.steps),
                "estimated_complexity": plan.estimated_complexity,
            },
        )
        self._plan = plan
        self._finalize_node(node, output=plan.model_dump())

    def on_sub_agent_start(
        self, sub_agent_id: str, name: str, step_number: int, tools: list[str]
    ) -> None:
        """Startet einen Sub-Agent Trace-Subtree."""
        node = self._create_trace_node(
            name=f"SubAgent: {name}",
            node_type=TraceNodeType.AGENT,
            metadata={
                "sub_agent_id": sub_agent_id,
                "step_number": step_number,
                "assigned_tools": tools,
            },
        )
        self._sub_agent_traces[sub_agent_id] = node.id

    def on_sub_agent_end(
        self, sub_agent_id: str, status: str,
        result_summary: str, duration_ms: int
    ) -> None:
        """Schließt einen Sub-Agent Trace-Subtree ab."""
        node_id = self._sub_agent_traces.get(sub_agent_id)
        if node_id:
            self._finalize_node_by_id(
                node_id,
                output={"status": status, "result_summary": result_summary},
                duration_ms=duration_ms,
            )

    def on_synthesis_start(self) -> None:
        """Startet den Synthesizer-Trace-Node."""
        self._create_trace_node(
            name="Synthesizer",
            node_type=TraceNodeType.AGENT,
        )

    def on_synthesis_end(self, final_response: str, duration_ms: int) -> None:
        """Schließt den Synthesizer-Trace-Node ab."""
        self._finalize_current_node(
            output={"response_length": len(final_response)},
            duration_ms=duration_ms,
        )
```

### 12.3 Trace-Baum-Struktur

**Single-Agent:**

```
Trace (root)
└── Agent Run
    ├── LLM Call (reasoning + tool decision)
    ├── Tool: search_knowledge_base
    │   └── HTTP Request
    ├── LLM Call (final response)
    └── (output: final text)
```

**Multi-Agent:**

```
Trace (root)
├── Planner
│   ├── LLM Call (plan generation)
│   └── (output: ExecutionPlan)
│
├── SubAgent: Wetter-Agent Berlin        [Step 1, parallel]
│   ├── LLM Call (reasoning)
│   ├── Tool: get_weather {city: Berlin}
│   ├── LLM Call (summarize)
│   └── (output: "Berlin: 12°C, bewölkt")
│
├── SubAgent: Wetter-Agent München       [Step 1, parallel]
│   ├── LLM Call (reasoning)
│   ├── Tool: get_weather {city: München}
│   ├── LLM Call (summarize)
│   └── (output: "München: 8°C, sonnig")
│
├── SubAgent: Wetter-Agent Hamburg       [Step 1, parallel]
│   ├── LLM Call (reasoning)
│   ├── Tool: get_weather {city: Hamburg}
│   ├── LLM Call (summarize)
│   └── (output: "Hamburg: 10°C, Regen")
│
├── SubAgent: Vergleichs-Agent           [Step 2, nach Step 1]
│   ├── LLM Call (comparison)
│   └── (output: "Vergleich...")
│
└── Synthesizer
    ├── LLM Call (final synthesis)
    └── (output: finale Antwort)
```

### 12.4 Integration mit StreamWriter

Der `ReActAgentTracer` kann optional mit einem `StreamWriter` gekoppelt werden. Dann emittiert er **automatisch** Stream-Events parallel zum Tracing:

```python
# Bei on_sub_agent_start → yield SUB_AGENT_START
# Bei on_tool_start     → yield TOOL_CALL_START (mit sub_agent_id)
# Bei on_tool_end       → yield TOOL_CALL_END (mit sub_agent_id)
# Bei on_sub_agent_end  → yield SUB_AGENT_END
```

Dadurch muss die Engine-Logik Streaming nicht separat implementieren — der Tracer übernimmt beides: **Trace-Erfassung + Stream-Event-Emission**.

```python
# Nutzung:
tracer = ReActAgentTracer(
    trace_id="trace_123",
    conversation_id="conv_456",
    message_id="msg_789",
    stream_writer=writer,  # Optional: koppelt Tracing an Streaming
)

engine = ReActAgentEngine(
    config=config,
    llm=llm,
    tools=tools,
    tracer=tracer,
)
```

### 12.5 Trace-Persistierung

Der fertige Trace wird — wie bei den bestehenden Tracern — nach Abschluss über `tracer.get_trace()` abgerufen und an den Agent-Service zurückgegeben. Der Agent-Service speichert ihn in der Traces-Collection (MongoDB/CosmosDB).

```python
# Nach engine.invoke_stream():
trace = tracer.get_trace()
# → Trace-Objekt mit allen Nodes (Planner, SubAgents, Tools, LLMs, Synthesizer)
# → Wird als Teil der SSE-Response oder via separatem Callback zurückgegeben
```

---

## 13. Offene Fragen / Diskussionspunkte

| # | Frage | Optionen |
|---|-------|----------|
| 1 | **SDK als Sidecar oder eingebettet?** | (A) Eigenständiger Python-Service, Agent-Service ruft ihn via HTTP auf. Saubere Trennung, unabhängig deploybar. (B) SDK direkt im Agent-Service eingebettet via CGo/Python-Subprocess. Weniger Netzwerk-Overhead, aber komplexer. |
| 2 | **Planner: LLM oder Rule-Based?** | (A) LLM-basiert mit Structured Output — flexibel, aber teurer und mit Halluzinations-Risiko. (B) Rule-based Heuristik — deterministisch, aber weniger adaptiv. (C) Hybrid: Rule-based für simple Anfragen, LLM für komplexe. |
| 3 | **Re-Planning?** | Soll der Orchestrator nach einem fehlgeschlagenen Sub-Agent den Plan anpassen können? Oder: starr den Plan abarbeiten und Fehler eskalieren? |
| 4 | **Sub-Agent Content streamen?** | (A) Ja — `SUB_AGENT_STREAM` zeigt Live-Output jedes Sub-Agents. Mehr Transparenz, aber visuell komplex. (B) Nein — nur `SUB_AGENT_START` + `SUB_AGENT_END` mit `result_summary`. Cleaner UI. |
| 5 | **Synthesizer vs. letzter Sub-Agent** | Wenn der Plan nur 1 Step mit 1 Task hat → braucht es den Synthesizer? Oder reicht der Direct-Output des einzelnen Sub-Agents? |
| 6 | **Tool-Config Schema** | Soll `tool.config` für MCP/OpenAPI ein striktes Schema bekommen (Pydantic-Validierung), oder bleibt es free-form `dict`? |
| 7 | **Chat-History an Sub-Agents** | Bekommen Sub-Agents die gesamte Chat-History oder nur den Task-Kontext? (Token-Verbrauch vs. Kontextqualität) |
| 8 | **Fallback auf Single-Agent** | Wenn der Planner entscheidet "diese Anfrage braucht keinen Multi-Agent-Plan" — fällt er automatisch auf den Single-Agent-Modus zurück? |
| 9 | **Tracer-StreamWriter-Kopplung** | (A) Tracer emittiert automatisch Stream-Events (Dual-Use: Trace + Stream). Weniger Code, aber enge Kopplung. (B) Tracer und StreamWriter bleiben getrennt — Engine emittiert Stream-Events explizit. Flexibler, aber doppelter Code. |
| 10 | **Sub-Agent Trace Granularität** | Sollen Sub-Agent-Traces die volle LLM-Call-Tiefe haben (Input/Output pro Token) oder nur aggregierte Summaries? (Token-Verbrauch der Trace-Daten vs. Debugging-Wert) |

---

## 14. Zusammenfassung

```
ReACT Agent Engine:

Single-Agent:
  ReActAgentEngine → LangGraph ReACT → Tools → Stream (ADR-001)

Multi-Agent:
  ReActAgentEngine → OrchestratorGraph
    ├── PlannerNode      → ExecutionPlan (Structured Output)
    ├── ExecutorNode     → SubAgents (parallel + sequentiell)
    │   ├── Step 1: [Agent-A ∥ Agent-B ∥ Agent-C]
    │   └── Step 2: [Agent-D] (abhängig von Step 1)
    └── SynthesizerNode  → Finale Antwort

Neue Stream-Events (→ ADR-001 Erweiterung):
  PLAN_START, PLAN_STREAM, PLAN_COMPLETE,
  SUB_AGENT_START, SUB_AGENT_STREAM, SUB_AGENT_END,
  SYNTHESIS_START, SYNTHESIS_STREAM

Tool-Integration:
  OpenAPI Spec → LangChain Tools (HTTP)
  MCP Server   → LangChain Tools (MCP Client)

Tracing:
  ReActAgentTracer (extends UnifiedUILanggraphTracer)
    ├── Planner Trace-Node
    ├── SubAgent Trace-Subtrees (parallel-korreliert)
    ├── Tool-Call Trace-Nodes (mit sub_agent_id)
    └── Synthesizer Trace-Node
  Optional: StreamWriter-Kopplung → Dual-Use (Trace + Stream)

Tool-Integration:
  OpenAPI Spec → LangChain Tools (HTTP)
  MCP Server   → LangChain Tools (MCP Client)

Konfiguration:
  System Prompt + Security + Tool Use + Response Format
  + multi_agent_enabled Toggle
  + max_iterations, max_sub_agents, max_parallel, etc.
```
