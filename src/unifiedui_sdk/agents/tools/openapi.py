"""OpenAPI tool integration — converts OpenAPI specs to LangChain tools."""

from __future__ import annotations

import json
from typing import Any

import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, create_model

from unifiedui_sdk.agents.config import ToolAuthType


def _build_args_model(
    operation_id: str,
    parameters: list[dict[str, Any]],
    request_body: dict[str, Any] | None,
) -> type[BaseModel]:
    """Build a Pydantic model from OpenAPI parameters and request body."""
    fields: dict[str, Any] = {}

    for param in parameters:
        name = param.get("name", "")
        required = param.get("required", False)
        schema = param.get("schema", {})
        desc = param.get("description", "")
        param_type = _schema_to_python_type(schema)

        if required:
            fields[name] = (param_type, Field(description=desc))
        else:
            fields[name] = (param_type | None, Field(default=None, description=desc))

    if request_body:
        content = request_body.get("content", {})
        json_schema = content.get("application/json", {}).get("schema", {})
        if json_schema:
            props = json_schema.get("properties", {})
            required_fields = set(json_schema.get("required", []))
            for prop_name, prop_schema in props.items():
                desc = prop_schema.get("description", "")
                prop_type = _schema_to_python_type(prop_schema)
                if prop_name in required_fields:
                    fields[prop_name] = (prop_type, Field(description=desc))
                else:
                    fields[prop_name] = (prop_type | None, Field(default=None, description=desc))

    if not fields:
        fields["placeholder"] = (str | None, Field(default=None, description="No parameters"))

    return create_model(f"{operation_id}Args", **fields)


def _schema_to_python_type(schema: dict[str, Any]) -> type:
    """Map an OpenAPI schema type to a Python type."""
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


def _build_auth_headers(auth_type: ToolAuthType, credential: str | None) -> dict[str, str]:
    """Build HTTP headers based on auth type and credential."""
    if not credential:
        return {}
    if auth_type == ToolAuthType.BEARER:
        return {"Authorization": f"Bearer {credential}"}
    if auth_type == ToolAuthType.API_KEY_HEADER:
        return {"X-API-Key": credential}
    if auth_type == ToolAuthType.BASIC:
        import base64

        encoded = base64.b64encode(credential.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {}


def _resolve_spec(spec: dict[str, Any] | str) -> dict[str, Any]:
    """Resolve an OpenAPI spec from a dict or JSON/YAML string."""
    if isinstance(spec, dict):
        return spec
    try:
        return json.loads(spec)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        try:
            import yaml

            return yaml.safe_load(spec)  # type: ignore[no-any-return]
        except Exception:
            msg = "Failed to parse OpenAPI spec as JSON or YAML"
            raise ValueError(msg) from None


def _extract_operations(
    spec: dict[str, Any],
    selected_operations: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Extract operations from an OpenAPI spec."""
    operations: list[dict[str, Any]] = []
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if operation is None:
                continue
            op_id = operation.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
            if selected_operations and op_id not in selected_operations:
                continue
            operations.append(
                {
                    "operation_id": op_id,
                    "method": method.upper(),
                    "path": path,
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "parameters": [
                        *path_item.get("parameters", []),
                        *operation.get("parameters", []),
                    ],
                    "request_body": operation.get("requestBody"),
                }
            )

    return operations


def openapi_to_langchain_tools(
    spec: dict[str, Any] | str,
    base_url: str,
    *,
    credential: str | None = None,
    auth_type: ToolAuthType = ToolAuthType.NONE,
    selected_operations: list[str] | None = None,
    timeout: int = 30,
) -> list[StructuredTool]:
    """Convert an OpenAPI spec into LangChain StructuredTool instances.

    Each operation in the spec becomes a separate tool that makes HTTP
    requests to the API.

    Args:
        spec: OpenAPI 3.x specification as a dict or JSON/YAML string.
        base_url: Base URL for the API requests.
        credential: Optional credential for authentication.
        auth_type: Authentication type for the API.
        selected_operations: If provided, only include these operationIds.
        timeout: HTTP request timeout in seconds.

    Returns:
        List of LangChain StructuredTool instances.
    """
    parsed_spec = _resolve_spec(spec)
    operations = _extract_operations(parsed_spec, selected_operations)
    auth_headers = _build_auth_headers(auth_type, credential)
    tools: list[StructuredTool] = []

    for op in operations:
        op_id = op["operation_id"]
        method = op["method"]
        path = op["path"]
        description = op.get("summary") or op.get("description") or op_id

        args_model = _build_args_model(op_id, op["parameters"], op.get("request_body"))

        def _make_runner(
            _method: str = method,
            _path: str = path,
            _base_url: str = base_url,
            _auth_headers: dict[str, str] = auth_headers,
            _timeout: int = timeout,
            _parameters: list[dict[str, Any]] = op["parameters"],
        ) -> Any:
            def run_tool(**kwargs: Any) -> str:
                url = _base_url.rstrip("/") + _path

                path_params = {p["name"] for p in _parameters if p.get("in") == "path"}
                query_params_spec = {p["name"] for p in _parameters if p.get("in") == "query"}
                header_params_spec = {p["name"] for p in _parameters if p.get("in") == "header"}

                for pname in path_params:
                    if pname in kwargs:
                        url = url.replace(f"{{{pname}}}", str(kwargs.pop(pname)))

                query_params = {k: v for k, v in kwargs.items() if k in query_params_spec and v is not None}
                header_params = {k: v for k, v in kwargs.items() if k in header_params_spec and v is not None}
                body_params = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in path_params
                    and k not in query_params_spec
                    and k not in header_params_spec
                    and k != "placeholder"
                    and v is not None
                }

                headers = {**_auth_headers, **header_params}

                with httpx.Client(timeout=_timeout) as client:
                    response = client.request(
                        method=_method,
                        url=url,
                        params=query_params if query_params else None,
                        json=body_params if body_params and _method in ("POST", "PUT", "PATCH") else None,
                        headers=headers if headers else None,
                    )
                    response.raise_for_status()
                    return response.text

            return run_tool

        tool = StructuredTool.from_function(
            func=_make_runner(),
            name=op_id,
            description=description,
            args_schema=args_model,
        )
        tools.append(tool)

    return tools
