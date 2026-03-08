"""MCP tool integration — connects to MCP servers and converts tools to LangChain tools."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model


def _json_schema_to_python_type(schema: dict[str, Any]) -> type:
    """Map a JSON Schema type to a Python type."""
    type_map: dict[str, type] = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
    }
    schema_type = schema.get("type", "string")
    if schema_type == "array":
        return list
    if schema_type == "object":
        return dict
    return type_map.get(schema_type, str)


def _build_args_model_from_json_schema(name: str, input_schema: dict[str, Any]) -> type[BaseModel]:
    """Build a Pydantic model from an MCP tool's JSON Schema inputSchema."""
    fields: dict[str, Any] = {}
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    for prop_name, prop_schema in properties.items():
        desc = prop_schema.get("description", "")
        prop_type = _json_schema_to_python_type(prop_schema)
        if prop_name in required:
            fields[prop_name] = (prop_type, Field(description=desc))
        else:
            fields[prop_name] = (prop_type | None, Field(default=None, description=desc))

    if not fields:
        fields["placeholder"] = (str | None, Field(default=None, description="No parameters"))

    return create_model(f"{name}Args", **fields)


async def mcp_to_langchain_tools(
    config: dict[str, Any],
    *,
    credential: str | None = None,
) -> list[StructuredTool]:
    """Connect to an MCP server and convert its tools to LangChain StructuredTools.

    Supports SSE and streamable HTTP transports. For the MCP client connection,
    requires the ``mcp`` package to be installed.

    Args:
        config: MCP server configuration with ``transport``, ``url`` (for SSE/streamable_http),
            or ``command``/``args`` (for stdio).
        credential: Optional credential passed as Bearer token in headers.

    Returns:
        List of LangChain StructuredTool instances.

    Raises:
        ImportError: If the ``mcp`` package is not installed.
        ValueError: If the transport type is not supported.
    """
    transport = config.get("transport", "sse")

    if transport in ("sse", "streamable_http"):
        return await _connect_sse_or_http(config, credential)
    if transport == "stdio":
        return await _connect_stdio(config)

    msg = f"Unsupported MCP transport: {transport}"
    raise ValueError(msg)


async def _connect_sse_or_http(
    config: dict[str, Any],
    credential: str | None = None,
) -> list[StructuredTool]:
    """Connect to an MCP server via SSE or streamable HTTP."""
    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client
    except ImportError:
        msg = "The 'mcp' package is required for MCP tool integration. Install with: pip install mcp"
        raise ImportError(msg) from None

    url = config["url"]
    headers: dict[str, str] = dict(config.get("headers", {}))
    if credential:
        headers["Authorization"] = f"Bearer {credential}"

    async with (
        sse_client(url=url, headers=headers) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        return await _session_to_tools(session)


async def _connect_stdio(config: dict[str, Any]) -> list[StructuredTool]:
    """Connect to an MCP server via stdio transport."""
    try:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client
    except ImportError:
        msg = "The 'mcp' package is required for MCP tool integration. Install with: pip install mcp"
        raise ImportError(msg) from None

    server_params = StdioServerParameters(
        command=config["command"],
        args=config.get("args", []),
        env=config.get("env"),
    )

    async with (
        stdio_client(server_params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        return await _session_to_tools(session)


async def _session_to_tools(session: Any) -> list[StructuredTool]:
    """Convert all tools in an MCP session to LangChain tools."""
    tools_result = await session.list_tools()
    tools: list[StructuredTool] = []

    for mcp_tool in tools_result.tools:
        tool_name = mcp_tool.name
        tool_description = mcp_tool.description or tool_name
        input_schema = mcp_tool.inputSchema if hasattr(mcp_tool, "inputSchema") else {}

        args_model = _build_args_model_from_json_schema(tool_name, input_schema)

        def _make_runner(_session: Any = session, _tool_name: str = tool_name) -> Any:
            def run_tool(**kwargs: Any) -> str:
                import asyncio

                filtered_kwargs = {k: v for k, v in kwargs.items() if k != "placeholder" and v is not None}

                async def _call() -> str:
                    result = await _session.call_tool(_tool_name, arguments=filtered_kwargs)
                    if hasattr(result, "content"):
                        parts = []
                        for item in result.content:
                            if hasattr(item, "text"):
                                parts.append(item.text)
                            else:
                                parts.append(str(item))
                        return "\n".join(parts)
                    return json.dumps(result) if not isinstance(result, str) else result

                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        return pool.submit(asyncio.run, _call()).result()
                return asyncio.run(_call())

            return run_tool

        tool = StructuredTool.from_function(
            func=_make_runner(),
            name=tool_name,
            description=tool_description,
            args_schema=args_model,
        )
        tools.append(tool)

    return tools
