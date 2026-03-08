"""Tests for tool loader."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unifiedui_sdk.agents.config import ToolAuthType, ToolConfig, ToolType
from unifiedui_sdk.agents.tools.loader import (
    _load_mcp_tools,
    _load_openapi_tools,
    load_tools,
)


def _make_tool(name: str) -> MagicMock:
    """Create a mock StructuredTool."""
    t = MagicMock()
    t.name = name
    return t


class TestLoadTools:
    """Tests for load_tools orchestration."""

    @pytest.mark.asyncio
    async def test_empty_configs(self) -> None:
        result = await load_tools([])
        assert result == []

    @pytest.mark.asyncio
    async def test_openapi_tools(self) -> None:
        cfg = ToolConfig(
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_inline": "{}", "base_url": "http://localhost"},
        )

        mock_tools = [_make_tool("op1"), _make_tool("op2")]

        with patch(
            "unifiedui_sdk.agents.tools.loader._load_openapi_tools",
            new_callable=AsyncMock,
            return_value=mock_tools,
        ):
            result = await load_tools([cfg])

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_mcp_tools(self) -> None:
        cfg = ToolConfig(
            type=ToolType.MCP_SERVER,
            config={"transport": "sse", "url": "http://localhost"},
        )

        mock_tools = [_make_tool("mcp_t1")]

        with patch(
            "unifiedui_sdk.agents.tools.loader._load_mcp_tools",
            new_callable=AsyncMock,
            return_value=mock_tools,
        ):
            result = await load_tools([cfg])

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_mixed_tools(self) -> None:
        openapi_cfg = ToolConfig(
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_inline": "{}", "base_url": "http://localhost"},
        )
        mcp_cfg = ToolConfig(
            type=ToolType.MCP_SERVER,
            config={"transport": "sse", "url": "http://mcp"},
        )

        with (
            patch(
                "unifiedui_sdk.agents.tools.loader._load_openapi_tools",
                new_callable=AsyncMock,
                return_value=[_make_tool("api_op")],
            ),
            patch(
                "unifiedui_sdk.agents.tools.loader._load_mcp_tools",
                new_callable=AsyncMock,
                return_value=[_make_tool("mcp_op")],
            ),
        ):
            result = await load_tools([openapi_cfg, mcp_cfg])

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_exception_from_loader_is_skipped(self) -> None:
        cfg = ToolConfig(
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_inline": "{}", "base_url": "http://localhost"},
        )

        with patch(
            "unifiedui_sdk.agents.tools.loader._load_openapi_tools",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            result = await load_tools([cfg])

        assert result == []


class TestLoadOpenAPITools:
    """Tests for _load_openapi_tools helper."""

    @pytest.mark.asyncio
    async def test_inline_spec(self) -> None:
        cfg = ToolConfig(
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_inline": '{"paths": {}}', "base_url": "http://api"},
        )

        with patch(
            "unifiedui_sdk.agents.tools.loader.openapi_to_langchain_tools",
            return_value=[_make_tool("t")],
        ):
            result = await _load_openapi_tools(cfg)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_spec_url_download(self) -> None:
        cfg = ToolConfig(
            type=ToolType.OPENAPI_DEFINITION,
            config={"spec_url": "https://example.com/spec.json", "base_url": "http://api"},
            credential="token123",
            auth_type=ToolAuthType.BEARER,
        )

        mock_response = MagicMock()
        mock_response.text = '{"paths": {}}'
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch(
                "unifiedui_sdk.agents.tools.loader.openapi_to_langchain_tools",
                return_value=[_make_tool("t")],
            ),
        ):
            result = await _load_openapi_tools(cfg)

        assert len(result) == 1


class TestLoadMCPTools:
    """Tests for _load_mcp_tools helper."""

    @pytest.mark.asyncio
    async def test_delegates_to_mcp(self) -> None:
        cfg = ToolConfig(
            type=ToolType.MCP_SERVER,
            config={"transport": "sse", "url": "http://mcp"},
            credential="secret",
        )

        with patch(
            "unifiedui_sdk.agents.tools.mcp.mcp_to_langchain_tools",
            new_callable=AsyncMock,
            return_value=[_make_tool("mcp_t")],
        ) as mock_mcp:
            result = await _load_mcp_tools(cfg)

        assert len(result) == 1
        mock_mcp.assert_called_once()
