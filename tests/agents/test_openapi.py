"""Tests for OpenAPI tool integration."""

from __future__ import annotations

import json

from unifiedui_sdk.agents.config import ToolAuthType
from unifiedui_sdk.agents.tools.openapi import (
    _build_args_model,
    _build_auth_headers,
    _extract_operations,
    _resolve_spec,
    _schema_to_python_type,
    openapi_to_langchain_tools,
)

SAMPLE_SPEC: dict = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "1.0"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "summary": "List all items",
                "parameters": [
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer"},
                        "description": "Max items to return",
                    }
                ],
            },
            "post": {
                "operationId": "createItem",
                "summary": "Create an item",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string", "description": "Item name"},
                                    "price": {"type": "number", "description": "Item price"},
                                },
                                "required": ["name"],
                            }
                        }
                    }
                },
            },
        },
        "/items/{item_id}": {
            "get": {
                "operationId": "getItem",
                "summary": "Get an item by ID",
                "parameters": [
                    {
                        "name": "item_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "The item ID",
                    }
                ],
            },
        },
    },
}


class TestSchemaToType:
    """Tests for _schema_to_python_type."""

    def test_string(self) -> None:
        assert _schema_to_python_type({"type": "string"}) is str

    def test_integer(self) -> None:
        assert _schema_to_python_type({"type": "integer"}) is int

    def test_number(self) -> None:
        assert _schema_to_python_type({"type": "number"}) is float

    def test_boolean(self) -> None:
        assert _schema_to_python_type({"type": "boolean"}) is bool

    def test_array(self) -> None:
        assert _schema_to_python_type({"type": "array"}) is list

    def test_object(self) -> None:
        assert _schema_to_python_type({"type": "object"}) is dict

    def test_unknown_defaults_to_str(self) -> None:
        assert _schema_to_python_type({"type": "foobar"}) is str

    def test_missing_type_defaults_to_str(self) -> None:
        assert _schema_to_python_type({}) is str


class TestBuildAuthHeaders:
    """Tests for _build_auth_headers."""

    def test_no_credential(self) -> None:
        result = _build_auth_headers(ToolAuthType.BEARER, None)
        assert result == {}

    def test_bearer(self) -> None:
        result = _build_auth_headers(ToolAuthType.BEARER, "my-token")
        assert result == {"Authorization": "Bearer my-token"}

    def test_api_key_header(self) -> None:
        result = _build_auth_headers(ToolAuthType.API_KEY_HEADER, "my-key")
        assert result == {"X-API-Key": "my-key"}

    def test_basic(self) -> None:
        import base64

        result = _build_auth_headers(ToolAuthType.BASIC, "user:pass")
        expected = base64.b64encode(b"user:pass").decode()
        assert result == {"Authorization": f"Basic {expected}"}

    def test_none_type(self) -> None:
        result = _build_auth_headers(ToolAuthType.NONE, "some-cred")
        assert result == {}

    def test_api_key_query_returns_empty(self) -> None:
        result = _build_auth_headers(ToolAuthType.API_KEY_QUERY, "key")
        assert result == {}


class TestResolveSpec:
    """Tests for _resolve_spec."""

    def test_dict_passthrough(self) -> None:
        spec = {"openapi": "3.0.0"}
        result = _resolve_spec(spec)
        assert result == spec

    def test_json_string(self) -> None:
        spec_str = json.dumps(SAMPLE_SPEC)
        result = _resolve_spec(spec_str)
        assert result["openapi"] == "3.0.0"

    def test_plain_string_parsed_as_yaml(self) -> None:
        """When yaml is available, a plain string is parsed by yaml.safe_load."""
        result = _resolve_spec("hello")
        assert result == "hello"


class TestExtractOperations:
    """Tests for _extract_operations."""

    def test_extracts_all_operations(self) -> None:
        ops = _extract_operations(SAMPLE_SPEC)
        op_ids = {op["operation_id"] for op in ops}
        assert op_ids == {"listItems", "createItem", "getItem"}

    def test_selected_operations(self) -> None:
        ops = _extract_operations(SAMPLE_SPEC, selected_operations=["listItems"])
        assert len(ops) == 1
        assert ops[0]["operation_id"] == "listItems"

    def test_operation_has_required_fields(self) -> None:
        ops = _extract_operations(SAMPLE_SPEC)
        for op in ops:
            assert "operation_id" in op
            assert "method" in op
            assert "path" in op
            assert "parameters" in op

    def test_get_item_has_path_param(self) -> None:
        ops = _extract_operations(SAMPLE_SPEC)
        get_item = next(o for o in ops if o["operation_id"] == "getItem")
        assert any(p["name"] == "item_id" for p in get_item["parameters"])

    def test_empty_paths(self) -> None:
        spec = {"openapi": "3.0.0", "paths": {}}
        ops = _extract_operations(spec)
        assert ops == []


class TestBuildArgsModel:
    """Tests for _build_args_model."""

    def test_query_params(self) -> None:
        params = [
            {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
            {"name": "offset", "in": "query", "required": True, "schema": {"type": "integer"}},
        ]
        model = _build_args_model("test_op", params, None)
        fields = model.model_fields
        assert "limit" in fields
        assert "offset" in fields

    def test_request_body(self) -> None:
        body = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "age": {"type": "integer"},
                        },
                        "required": ["name"],
                    }
                }
            }
        }
        model = _build_args_model("test_op", [], body)
        fields = model.model_fields
        assert "name" in fields
        assert "age" in fields

    def test_empty_params_gets_placeholder(self) -> None:
        model = _build_args_model("test_op", [], None)
        assert "placeholder" in model.model_fields


class TestOpenAPIToLangchainTools:
    """Tests for openapi_to_langchain_tools."""

    def test_creates_tools(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
        )
        assert len(tools) == 3

    def test_tool_names(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
        )
        names = {t.name for t in tools}
        assert names == {"listItems", "createItem", "getItem"}

    def test_tool_description(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
        )
        list_tool = next(t for t in tools if t.name == "listItems")
        assert "List all items" in list_tool.description

    def test_selected_operations(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
            selected_operations=["getItem"],
        )
        assert len(tools) == 1
        assert tools[0].name == "getItem"

    def test_json_string_spec(self) -> None:
        spec_json = json.dumps(SAMPLE_SPEC)
        tools = openapi_to_langchain_tools(
            spec=spec_json,
            base_url="https://api.example.com",
        )
        assert len(tools) == 3

    def test_tools_have_args_schema(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
        )
        for tool in tools:
            assert tool.args_schema is not None

    def test_with_auth(self) -> None:
        tools = openapi_to_langchain_tools(
            spec=SAMPLE_SPEC,
            base_url="https://api.example.com",
            credential="my-token",
            auth_type=ToolAuthType.BEARER,
        )
        assert len(tools) == 3

    def test_empty_spec(self) -> None:
        spec = {"openapi": "3.0.0", "paths": {}}
        tools = openapi_to_langchain_tools(spec=spec, base_url="http://localhost")
        assert tools == []
