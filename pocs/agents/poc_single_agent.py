"""POC: Single-agent ReACT with local tools.

Demonstrates:
- ReActAgentEngine in single-agent mode
- Custom local tools (calculator, string manipulation)
- Streaming output with reasoning and tool calls
- ReActAgentTracer for trace capture

Run:
    uv run --group poc python pocs/agents/poc_single_agent.py
"""

import asyncio
import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI

from unifiedui_sdk.agents import ReActAgentConfig, ReActAgentEngine
from unifiedui_sdk.tracing import ReActAgentTracer

load_dotenv()


# --- Local tools ---


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression and return the result.

    Args:
        expression: A mathematical expression like '2 + 3 * 4'.
    """
    try:
        result = eval(expression, {"__builtins__": {}})  # noqa: S307
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {e}"


@tool
def word_count(text: str) -> str:
    """Count the number of words in a text.

    Args:
        text: The text to count words in.
    """
    count = len(text.split())
    return f"Word count: {count}"


@tool
def reverse_string(text: str) -> str:
    """Reverse a string.

    Args:
        text: The string to reverse.
    """
    return f"Reversed: {text[::-1]}"


async def main() -> None:
    """Run the single-agent POC."""
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
        system_prompt="You are a helpful assistant with access to tools. Use them when needed.",
        tool_use_prompt="Always show your reasoning before using tools.",
        max_iterations=10,
    )

    tracer = ReActAgentTracer()

    engine = ReActAgentEngine(
        config=config,
        llm=llm,
        tools=[calculator, word_count, reverse_string],
        tracer=tracer,
    )

    print("=" * 60)
    print("Single-Agent POC")
    print("=" * 60)

    message = "Calculate 42 * 17, then count the words in 'The quick brown fox jumps over the lazy dog', and reverse the word 'unified'"

    print(f"\nUser: {message}\n")
    print("-" * 60)

    async for msg in engine.invoke_stream(message):
        if msg.type == "TEXT_STREAM":
            print(msg.content, end="", flush=True)
        elif msg.type == "REASONING_START":
            print("\n💭 [Reasoning]", end="", flush=True)
        elif msg.type == "REASONING_STREAM":
            print(msg.content, end="", flush=True)
        elif msg.type == "REASONING_END":
            print("\n", end="", flush=True)
        elif msg.type == "TOOL_CALL_START":
            print(f"\n🔧 Tool: {msg.config.get('tool_name')} | Args: {msg.config.get('tool_arguments')}")
        elif msg.type == "TOOL_CALL_END":
            status = msg.config.get("tool_status")
            result = msg.config.get("tool_result", "")[:200]
            duration = msg.config.get("tool_duration_ms", "?")
            print(f"   → {status} ({duration}ms): {result}")
        elif msg.type == "STREAM_END":
            print("\n" + "-" * 60)
        elif msg.type == "TRACE":
            trace_data = msg.config
            node_count = len(trace_data.get("nodes", []))
            print(f"\n📊 Trace: {node_count} top-level nodes")

    print("\n✅ Done")


if __name__ == "__main__":
    asyncio.run(main())
