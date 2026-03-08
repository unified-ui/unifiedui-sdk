"""Tests for MCP tool integration helper functions."""

from __future__ import annotations

from unifiedui_sdk.agents.tools.mcp import (
    _build_args_model_from_json_schema,
    _json_schema_to_python_type,
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
