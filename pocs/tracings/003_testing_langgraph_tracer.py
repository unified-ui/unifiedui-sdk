"""POC 003 — Testing the LangGraph tracer with a real Azure OpenAI agent.

Demonstrates UnifiedUILanggraphTracer filtering __start__/__end__ nodes
while capturing the same trace structure as POC 002 (LangChain tracer).
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langchain.agents import create_agent

from unifiedui_sdk.tracing import UnifiedUILanggraphTracer

load_dotenv()


# --- Simple tools (same as POC 002) ---


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city.

    Args:
        city: Name of the city.

    Returns:
        Weather description string.
    """
    weather_data = {
        "Berlin": "18°C, partly cloudy",
        "New York": "22°C, sunny",
        "Tokyo": "15°C, rainy",
        "London": "12°C, foggy",
    }
    return weather_data.get(city, f"Weather data not available for {city}")


@tool
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression.

    Args:
        expression: A math expression to evaluate (e.g., '2 + 2').

    Returns:
        The result as a string.
    """
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def get_population(country: str) -> str:
    """Get the approximate population of a country.

    Args:
        country: Name of the country.

    Returns:
        Population description string.
    """
    populations = {
        "Germany": "84 million",
        "USA": "331 million",
        "Japan": "125 million",
        "UK": "67 million",
    }
    return populations.get(country, f"Population data not available for {country}")


def main() -> None:
    # 1. Setup Azure OpenAI
    llm = AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        temperature=0,
    )

    # 2. Define tools
    tools = [get_weather, calculate, get_population]

    # 3. Create ReAct agent using LangChain
    agent = create_agent(llm, tools)

    # 4. Create the LangGraph tracer (filters __start__/__end__)
    tracer = UnifiedUILanggraphTracer()

    # 5. Run the agent with the tracer
    print("=" * 80)
    print("Running LangGraph agent with UnifiedUILanggraphTracer")
    print("Query: 'What is the weather in Berlin and Tokyo? Also calculate 42 * 17.'")
    print("=" * 80)

    result = agent.invoke(
        {"messages": [("human", "What is the weather in Berlin and Tokyo? Also calculate 42 * 17.")]},
        config={"callbacks": [tracer]},
    )

    print("\n" + "=" * 80)
    print("Agent Result:")
    last_msg = result["messages"][-1]
    print(last_msg.content)
    print("=" * 80)

    # 6. Get traces
    trace = tracer.get_trace()
    trace_dict = trace.to_dict()

    print("\n=== Trace as Dict (camelCase JSON) ===")
    print(json.dumps(trace_dict, indent=2, default=str))

    # 7. Verify — no __start__ or __end__ nodes
    print("\n=== Trace Summary ===")
    print(f"Trace ID: {trace.id}")
    print(f"Top-level nodes: {len(trace.nodes)}")

    all_node_names: list[str] = []

    for i, node in enumerate(trace.nodes):
        all_node_names.append(node.name)
        print(f"\n  Node [{i}]: {node.name} ({node.type}) - {node.status}")
        print(f"    Duration: {node.duration:.4f}s")
        if node.data and node.data.input:
            print(f"    Input: {node.data.input.text[:100]}...")
        if node.data and node.data.output:
            print(f"    Output: {node.data.output.text[:100]}...")
        for j, child in enumerate(node.nodes):
            all_node_names.append(child.name)
            print(f"    Child [{j}]: {child.name} ({child.type}) - {child.status} [{child.duration:.4f}s]")
            for k, grandchild in enumerate(child.nodes):
                all_node_names.append(grandchild.name)
                print(
                    f"      Grandchild [{k}]: {grandchild.name} ({grandchild.type})"
                    f" - {grandchild.status} [{grandchild.duration:.4f}s]"
                )

    # 8. Verify filtering
    print("\n=== Filtering Verification ===")
    assert "__start__" not in all_node_names, "__start__ should be filtered!"
    assert "__end__" not in all_node_names, "__end__ should be filtered!"
    print("✅ __start__ and __end__ nodes correctly filtered!")
    print(f"   All node names: {all_node_names}")

    print("\n✅ LangGraph tracer POC completed!")


if __name__ == "__main__":
    main()
