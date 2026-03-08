"""POC: Multi-agent orchestration with local tools.

Demonstrates:
- ReActAgentEngine in multi-agent mode
- Planner → parallel Executor → Synthesizer pipeline
- Multiple sub-agents running in parallel
- Full streaming lifecycle with PLAN, SUB_AGENT, SYNTHESIS events

Run:
    uv run --group poc python pocs/agents/poc_multi_agent.py
"""

import asyncio
import os
import random

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.agents.config import MultiAgentConfig
from unifiedui_sdk.tracing import ReActAgentTracer

load_dotenv()


# --- Local tools simulating real APIs ---


@tool
def get_weather(city: str) -> str:
    """Get current weather data for a city.

    Args:
        city: Name of the city.
    """
    weather_data = {
        "Berlin": {"temp": 12, "condition": "cloudy", "humidity": 65},
        "München": {"temp": 8, "condition": "sunny", "humidity": 45},
        "Hamburg": {"temp": 10, "condition": "rainy", "humidity": 80},
        "Frankfurt": {"temp": 14, "condition": "partly cloudy", "humidity": 55},
        "Köln": {"temp": 11, "condition": "overcast", "humidity": 70},
    }
    data = weather_data.get(city, {"temp": random.randint(5, 25), "condition": "unknown", "humidity": random.randint(30, 90)})
    return f"Weather in {city}: {data['temp']}°C, {data['condition']}, {data['humidity']}% humidity"


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for relevant documents.

    Args:
        query: Search query string.
    """
    docs = {
        "architecture": "unified-ui is a multi-tenant platform with Agent-Service (Go/Gin), Platform-Service (Python/FastAPI), Frontend (React/TypeScript).",
        "deployment": "Deploy using Docker containers to Azure Container Apps. CI/CD via GitHub Actions.",
        "security": "RBAC with tenant isolation. JWT authentication via Entra ID. API key management.",
    }
    for key, value in docs.items():
        if key in query.lower():
            return f"Found: {value}"
    return f"No documents found for query: {query}"


@tool
def translate_text(text: str, target_language: str) -> str:
    """Translate text to a target language.

    Args:
        text: The text to translate.
        target_language: The target language (e.g., 'German', 'English').
    """
    return f"[Translated to {target_language}]: {text}"


async def main() -> None:
    """Run the multi-agent POC."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    if not all([endpoint, api_key, deployment, api_version]):
        print("ERROR: Set AZURE_OPENAI_* vars in .env")
        return

    llm = AzureChatOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=deployment,
        api_version=api_version,
        temperature=0.1,
    )

    config = ReActAgentConfig(
        system_prompt="You are a helpful research assistant.",
        multi_agent_enabled=True,
        multi_agent=MultiAgentConfig(
            max_sub_agents=5,
            max_parallel_per_step=3,
            sub_agent_max_iterations=5,
        ),
    )

    tracer = ReActAgentTracer()

    engine = ReActAgentEngine(
        config=config,
        llm=llm,
        tools=[get_weather, search_knowledge_base, translate_text],
        tracer=tracer,
    )

    print("=" * 60)
    print("Multi-Agent POC")
    print("=" * 60)

    message = "Get the current weather for Berlin, München, and Hamburg, then create a comparison summary."

    print(f"\nUser: {message}\n")
    print("-" * 60)

    async for msg in engine.invoke_stream(message):
        if msg.type == "STREAM_START":
            print("🚀 Stream started")
        elif msg.type == "PLAN_START":
            print("📋 Planning...")
        elif msg.type == "PLAN_STREAM":
            print(f"   💭 {msg.content}")
        elif msg.type == "PLAN_COMPLETE":
            plan = msg.config.get("plan", {})
            print(f"   ✅ Plan: {plan.get('goal', 'N/A')}")
            print(f"   Steps: {len(plan.get('steps', []))}, Complexity: {plan.get('estimated_complexity', 'N/A')}")
            for step_data in plan.get("steps", []):
                print(f"   Step {step_data.get('step_number')}: {len(step_data.get('tasks', []))} task(s)")
                for task_data in step_data.get("tasks", []):
                    print(f"     - {task_data.get('name')} (tools: {task_data.get('required_tool_names', [])})")
        elif msg.type == "SUB_AGENT_START":
            name = msg.config.get("sub_agent_name", "?")
            step_n = msg.config.get("step_number", "?")
            print(f"\n🤖 [{msg.config.get('sub_agent_id')}] {name} (Step {step_n})")
        elif msg.type == "TOOL_CALL_START":
            sub = msg.config.get("sub_agent_id", "")
            tn = msg.config.get("tool_name", "?")
            ta = msg.config.get("tool_arguments", {})
            prefix = f"   [{sub}] " if sub else "   "
            print(f"{prefix}🔧 {tn}({ta})")
        elif msg.type == "TOOL_CALL_END":
            sub = msg.config.get("sub_agent_id", "")
            result = msg.config.get("tool_result", "")[:100]
            prefix = f"   [{sub}] " if sub else "   "
            print(f"{prefix}→ {result}")
        elif msg.type == "SUB_AGENT_END":
            name = msg.config.get("sub_agent_name", "?")
            status = msg.config.get("status", "?")
            duration = msg.config.get("duration_ms", "?")
            print(f"   ✅ {name}: {status} ({duration}ms)")
        elif msg.type == "SYNTHESIS_START":
            print("\n🧪 Synthesizing final response...")
        elif msg.type == "SYNTHESIS_STREAM":
            print(msg.content, end="", flush=True)
        elif msg.type == "STREAM_END":
            print("\n" + "-" * 60)
        elif msg.type == "TRACE":
            trace_data = msg.config
            nodes = trace_data.get("nodes", [])
            print(f"\n📊 Trace: {len(nodes)} top-level nodes")
            for node in nodes:
                children = len(node.get("nodes", []))
                name = node.get("name", "?")
                status = node.get("status", "?")
                child_info = f" ({children} children)" if children else ""
                print(f"   - {name}: {status}{child_info}")

    print("\n✅ Done")


if __name__ == "__main__":
    asyncio.run(main())
