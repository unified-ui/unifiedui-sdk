"""Tool loader — orchestrates loading tools from multiple sources."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from unifiedui_sdk.agents.config import ToolAuthType, ToolConfig, ToolType

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool, StructuredTool

from unifiedui_sdk.agents.tools.openapi import openapi_to_langchain_tools


async def load_tools(tool_configs: list[ToolConfig]) -> list[BaseTool]:
    """Load all tools in parallel based on their type configuration.

    Args:
        tool_configs: List of tool configurations to load.

    Returns:
        Flat list of all loaded LangChain BaseTool instances.
    """
    tasks: list[asyncio.Task[list[StructuredTool]]] = []

    for tool_cfg in tool_configs:
        if tool_cfg.type == ToolType.OPENAPI_DEFINITION:
            tasks.append(
                asyncio.ensure_future(_load_openapi_tools(tool_cfg)),
            )
        elif tool_cfg.type == ToolType.MCP_SERVER:
            tasks.append(
                asyncio.ensure_future(_load_mcp_tools(tool_cfg)),
            )

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)

    tools: list[BaseTool] = []
    for result in results:
        if isinstance(result, BaseException):
            continue
        tools.extend(result)

    return tools


async def _load_openapi_tools(tool_cfg: ToolConfig) -> list[StructuredTool]:
    """Load tools from an OpenAPI spec configuration."""
    config: dict[str, Any] = dict(tool_cfg.config)
    spec = config.get("spec_inline") or config.get("spec_url", "")
    base_url = str(config.get("base_url", ""))
    selected = config.get("selected_operations")
    timeout = int(config.get("timeout_seconds", 30))

    if isinstance(spec, str) and spec.startswith(("http://", "https://")):
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(spec)
            response.raise_for_status()
            spec = response.text

    return openapi_to_langchain_tools(
        spec=spec,
        base_url=base_url,
        credential=tool_cfg.credential,
        auth_type=tool_cfg.auth_type or ToolAuthType.NONE,
        selected_operations=selected,
        timeout=timeout,
    )


async def _load_mcp_tools(tool_cfg: ToolConfig) -> list[StructuredTool]:
    """Load tools from an MCP server configuration."""
    from unifiedui_sdk.agents.tools.mcp import mcp_to_langchain_tools

    return await mcp_to_langchain_tools(
        config=dict(tool_cfg.config),
        credential=tool_cfg.credential,
    )
