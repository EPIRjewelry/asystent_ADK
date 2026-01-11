"""Utilities for converting MCP tool definitions to google-genai Tool objects."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from google.genai import types
from google.genai.types import Schema, Type


def _map_json_type_to_vertex_type(json_type: Optional[str]) -> Type:
    mapping = {
        "string": Type.STRING,
        "number": Type.NUMBER,
        "integer": Type.INTEGER,
        "boolean": Type.BOOLEAN,
        "array": Type.ARRAY,
        "object": Type.OBJECT,
    }
    if not json_type:
        return Type.OBJECT
    return mapping.get(json_type.lower(), Type.STRING)


def _convert_schema(schema_dict: Optional[Dict[str, Any]]) -> Schema:
    if not schema_dict:
        return Schema(type=Type.OBJECT)

    json_type = schema_dict.get("type", "object")
    vertex_type = _map_json_type_to_vertex_type(json_type)

    description = schema_dict.get("description")
    enum_vals = schema_dict.get("enum")
    fmt = schema_dict.get("format")

    properties = None
    if vertex_type == Type.OBJECT:
        raw_properties = schema_dict.get("properties") or {}
        properties = {
            key: _convert_schema(value)
            for key, value in raw_properties.items()
        } or None

    items = None
    if vertex_type == Type.ARRAY and "items" in schema_dict:
        items = _convert_schema(schema_dict["items"])

    required = schema_dict.get("required") or None

    return Schema(
        type=vertex_type,
        format=fmt,
        description=description,
        enum=enum_vals,
        properties=properties,
        required=required,
        items=items,
    )


def _sanitize_tool_name(name: str) -> str:
    sanitized = name.strip().replace("-", "_")
    return sanitized or "mcp_tool"


def convert_toolset_to_vertex_tools(toolset: Any) -> List[types.Tool]:
    tools: Iterable[Any] = getattr(toolset, "tools", []) or []
    declarations: List[types.FunctionDeclaration] = []

    for tool in tools:
        schema_dict = (
            getattr(tool, "inputSchema", None)
            or getattr(tool, "input_schema", None)
            or {}
        )
        declaration = types.FunctionDeclaration(
            name=_sanitize_tool_name(getattr(tool, "name", "mcp_tool")),
            description=getattr(tool, "description", ""),
            parameters=_convert_schema(schema_dict),
        )
        declarations.append(declaration)

    if not declarations:
        return []

    return [types.Tool(function_declarations=declarations)]
