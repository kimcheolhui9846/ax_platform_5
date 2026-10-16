"""Pydantic 모델의 JSON Schema를 따라 Mock 값을 자동으로 채운다.

output_schema를 고쳐도 Mock을 따로 고치지 않아도 되게 하려는 장치다. 흔한 제약(길이·개수·범위·
enum/const·문자열 형식)을 지키고, 자기 자신을 가리키는 스키마는 가장 작은 값(빈 목록·None·생략)으로 끊는다.
"""
import math
from typing import Any

from pydantic import BaseModel

_FORMATS = {
    "date-time": "2026-01-01T00:00:00Z",
    "date": "2026-01-01",
    "uuid": "00000000-0000-4000-8000-000000000000",
    "email": "mock@example.com",
}


class _Cycle(Exception):
    """$ref가 자기 자신으로 돌아왔다. 이 값을 비울 수 있는 자리(목록·null·선택 속성)까지 올라간다."""


def mock_instance(model: type[BaseModel]) -> BaseModel:
    schema = model.model_json_schema()
    try:
        data = _fill(schema, schema.get("$defs", {}), model.__name__, frozenset())
    except _Cycle:
        raise ValueError(f"{model.__name__}: 비울 수 없는 재귀 필드가 있어 Mock 값을 만들 수 없습니다.") from None
    return model.model_validate(data)


def _fill(schema: dict[str, Any], defs: dict[str, Any], name: str, path: frozenset[str]) -> Any:
    if "$ref" in schema:
        ref = schema["$ref"].split("/")[-1]
        if ref in path:
            raise _Cycle(ref)
        return _fill(defs[ref], defs, name, path | {ref})
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return _fill_union(schema[key], defs, name, path)
    if "allOf" in schema:
        return _fill(schema["allOf"][0], defs, name, path)

    match schema.get("type"):
        case "object":
            return _fill_object(schema, defs, path)
        case "array":
            return _fill_array(schema, defs, name, path)
        case "integer":
            return _number(schema, integer=True)
        case "number":
            return _number(schema, integer=False)
        case "boolean":
            return True
    return _string(schema, schema.get("description") or name)


def _fill_union(options: list[dict[str, Any]], defs: dict[str, Any], name: str, path: frozenset[str]) -> Any:
    nullable = any(s.get("type") == "null" for s in options)
    for option in (s for s in options if s.get("type") != "null"):
        try:
            return _fill(option, defs, name, path)
        except _Cycle:
            continue
    if nullable:
        return None
    raise _Cycle(name)


def _fill_object(schema: dict[str, Any], defs: dict[str, Any], path: frozenset[str]) -> dict[str, Any]:
    required = set(schema.get("required", []))
    data: dict[str, Any] = {}
    for key, sub in schema.get("properties", {}).items():
        try:
            data[key] = _fill(sub, defs, key, path)
        except _Cycle:
            if key in required:
                raise
    return data


def _fill_array(schema: dict[str, Any], defs: dict[str, Any], name: str, path: frozenset[str]) -> list[Any]:
    count = max(schema.get("minItems", 1), 1)
    if "maxItems" in schema:
        count = min(count, schema["maxItems"])
    if count == 0:
        return []
    try:
        return [_fill(schema.get("items", {}), defs, name, path) for _ in range(count)]
    except _Cycle:
        if schema.get("minItems", 0) > 0:
            raise
        return []


def _string(schema: dict[str, Any], label: str) -> str:
    if schema.get("format") in _FORMATS:
        return _FORMATS[schema["format"]]
    text = f"[mock] {label}"
    min_length = schema.get("minLength", 0)
    if len(text) < min_length:
        text += "x" * (min_length - len(text))
    if "maxLength" in schema:
        text = text[: schema["maxLength"]]
    return text


def _number(schema: dict[str, Any], *, integer: bool) -> int | float:
    """[순수] minimum·maximum·exclusiveMinimum·exclusiveMaximum을 지키는 값. 범위가 없으면 1 / 0.5."""
    lo, hi = schema.get("minimum"), schema.get("maximum")
    lo_ex, hi_ex = schema.get("exclusiveMinimum"), schema.get("exclusiveMaximum")

    def fits(v: float) -> bool:
        return (
            (lo is None or v >= lo)
            and (hi is None or v <= hi)
            and (lo_ex is None or v > lo_ex)
            and (hi_ex is None or v < hi_ex)
        )

    default = 1 if integer else 0.5
    if fits(default):
        return default
    if integer:
        low = lo if lo is not None else (math.floor(lo_ex) + 1 if lo_ex is not None else None)
        high = hi if hi is not None else (math.ceil(hi_ex) - 1 if hi_ex is not None else None)
        return math.ceil(low) if low is not None else math.floor(high)  # type: ignore[arg-type]
    low = lo if lo is not None else lo_ex
    high = hi if hi is not None else hi_ex
    if low is not None and high is not None:
        return (low + high) / 2
    return low + 1 if low is not None else high - 1  # type: ignore[operator]
