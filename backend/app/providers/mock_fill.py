"""Pydantic 모델의 JSON Schema를 따라 Mock 값을 자동으로 채운다.

output_schema를 고쳐도 Mock을 따로 고치지 않아도 되게 하려는 장치다.
"""
from typing import Any

from pydantic import BaseModel


def mock_instance(model: type[BaseModel]) -> BaseModel:
    schema = model.model_json_schema()
    data = _fill(schema, schema.get("$defs", {}), model.__name__)
    return model.model_validate(data)


def _fill(schema: dict[str, Any], defs: dict[str, Any], name: str) -> Any:
    if "$ref" in schema:
        return _fill(defs[schema["$ref"].split("/")[-1]], defs, name)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            return _fill(options[0], defs, name)
    if "allOf" in schema:
        return _fill(schema["allOf"][0], defs, name)

    kind = schema.get("type")
    label = schema.get("description") or name
    if kind == "object":
        properties = schema.get("properties", {})
        return {key: _fill(sub, defs, key) for key, sub in properties.items()}
    if kind == "array":
        count = max(schema.get("minItems", 1), 1)
        return [_fill(schema.get("items", {}), defs, name) for _ in range(count)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 0.5
    if kind == "boolean":
        return True
    if schema.get("format") == "date-time":
        return "2026-01-01T00:00:00Z"
    return f"[mock] {label}"
