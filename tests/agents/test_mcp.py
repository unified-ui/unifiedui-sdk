"""Tests for MCP tool integration helper functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unifiedui_sdk.agents.tools.mcp import (
    _build_args_model_from_json_schema,
    _json_schema_to_python_type,
    _session_to_tools,
    mcp_to_langchain_tools,
)


class TestJsonSchemaToType:
    """Tests for _json_schema_to_python_type."""

    def test_string(self) -> None:
        assert _json_schema_to_python_type({"type": "string"}) is str

    def test_integer(self) -> None:
        assert _json_schema_to_python_type({"type": "integer"}) is int

    def test_number(self) -> None:
        assert _json_schema_to_python_type({"type": "number"}) is float

    def test_boolean(self) -> None:
        assert _json_schema_to_python_type({"type": "boolean"}) is bool

    def test_array(self) -> None:
        assert _json_schema_to_python_type({"type": "array"}) is list

    def test_object(self) -> None:
        assert _json_schema_to_python_type({"type": "object"}) is dict

    def test_unknown_defaults_to_str(self) -> None:
        assert _json_schema_to_python_type({"type": "xyz"}) is str

    def test_missing_type_defaults_to_str(self) -> None:
        assert _json_schema_to_python_type({}) is str


class TestBuildArgsModelFromJsonSchema:
    """Tests for _build_args_model_from_json_schema."""

    def test_basic_properties(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name"},
                "count": {"type": "integer", "description": "Count"},
            },
            "required": ["name"],
        }
        model = _build_args_model_from_json_schema("test_tool", schema)
        fields = model.model_fields
        assert "name" in fields
        assert "count" in fields

    def test_empty_properties_gets_placeholder(self) -> None:
        schema = {"type": "object", "properties": {}}
        model = _build_args_model_from_json_schema("empty_tool", schema)
        assert "placeholder" in model.model_fields

    def test_no_properties_key_gets_placeholder(self) -> None:
        schema = {"type": "object"}
        model = _build_args_model_from_json_schema("no_props", schema)
        assert "placeholder" in model.model_fields

    def test_required_field_is_required(self) -> None:
        schema = {
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }
        model = _build_args_model_from_json_schema("test", schema)
        field = model.model_fields["name"]
        assert field.is_required()

    def test_optional_field_has_default_none(self) -> None:
        schema = {
            "properties": {"name": {"type": "string"}},
            "required": [],
        }
        model = _build_args_model_from_json_schema("test", schema)
        field = model.model_fields["name"]
        assert field.default is None

    def test_model_name_contains_tool_name(self) -> None:
        schema = {"properties": {"x": {"type": "string"}}, "required": ["x"]}
        model = _build_args_model_from_json_schema("my_tool", schema)
        assert "my_tool" in model.__name__


class TestMcpToLangchainTools:
    """Tests for mcp_to_langchain_tools dispatch."""

    @pytest.mark.asyncio
    async def test_sse_transport(self) -> None:
        with patch(
            "unifiedui_sdk.agents.tools.mcp._connect_sse_or_http",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ) as mock_conn:
            result = await mcp_to_langchain_tools(
                {"transport": "sse", "url": "http://localhost"},
            )

        assert len(result) == 1
        mock_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_streamable_http_transport(self) -> None:
        with patch(
            "unifiedui_sdk.agents.tools.mcp._connect_sse_or_http",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            result = await mcp_to_langchain_tools(
                {"transport": "streamable_http", "url": "http://localhost"},
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_stdio_transport(self) -> None:
        with patch(
            "unifiedui_sdk.agents.tools.mcp._connect_stdio",
            new_callable=AsyncMock,
            return_value=[MagicMock()],
        ):
            result = await mcp_to_langchain_tools({"transport": "stdio", "command": "node"})

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_default_transport_is_sse(self) -> None:
        with patch(
            "unifiedui_sdk.agents.tools.mcp._connect_sse_or_http",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_conn:
            await mcp_to_langchain_tools({"url": "http://localhost"})

        mock_conn.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsupported_transport_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported MCP transport"):
            await mcp_to_langchain_tools({"transport": "grpc"})

    @pytest.mark.asyncio
    async def test_with_credential(self) -> None:
        with patch(
            "unifiedui_sdk.agents.tools.mcp._connect_sse_or_http",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_conn:
            await mcp_to_langchain_tools(
                {"transport": "sse", "url": "http://localhost"},
                credential="token123",
            )

        mock_conn.assert_called_once_with(
            {"transport": "sse", "url": "http://localhost"},
            "token123",
        )


class TestSessionToTools:
    """Tests for _session_to_tools."""

    @pytest.mark.asyncio
    async def test_converts_tools(self) -> None:
        mcp_tool = MagicMock()
        mcp_tool.name = "my_tool"
        mcp_tool.description = "A test tool"
        mcp_tool.inputSchema = {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        }

        tools_result = MagicMock()
        tools_result.tools = [mcp_tool]

        session = AsyncMock()
        session.list_tools = AsyncMock(return_value=tools_result)

        result = await _session_to_tools(session)
        assert len(result) == 1
        assert result[0].name == "my_tool"
        assert result[0].description == "A test tool"

    @pytest.mark.asyncio
    async def test_tool_without_description(self) -> None:
        mcp_tool = MagicMock()
        mcp_tool.name = "bare_tool"
        mcp_tool.description = None
        mcp_tool.inputSchema = {"type": "object", "properties": {}}

        tools_result = MagicMock()
        tools_result.tools = [mcp_tool]

        session = AsyncMock()
        session.list_tools = AsyncMock(return_value=tools_result)

        result = await _session_to_tools(session)
        assert result[0].description == "bare_tool"

    @pytest.mark.asyncio
    async def test_tool_without_input_schema(self) -> None:
        mcp_tool = MagicMock(spec=[])
        mcp_tool.name = "no_schema"
        mcp_tool.description = "No schema"

        tools_result = MagicMock()
        tools_result.tools = [mcp_tool]

        session = AsyncMock()
        session.list_tools = AsyncMock(return_value=tools_result)

        result = await _session_to_tools(session)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_empty_tools_list(self) -> None:
        tools_result = MagicMock()
        tools_result.tools = []

        session = AsyncMock()
        session.list_tools = AsyncMock(return_value=tools_result)

        result = await _session_to_tools(session)
        assert result == []
