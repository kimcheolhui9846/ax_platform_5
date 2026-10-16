"""응답 계약: 응답에서 닿는 모든 컴포넌트 스키마는 모든 속성을 필수(required)로 낸다.

응답 필드는 언제나 채워져 나가므로(값이 null일 수는 있다) 생성된 프론트 타입이 선택 필드(`?:`)로
느슨해지면 안 된다. 응답에 실리는 모델을 새로 만들면 이 테스트가 ContractModel 상속 누락을 잡는다.
"""
from typing import Any

from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.mock import MockProvider

# 개발 모드에서만 채워지는 선택 필드. 문서에 그렇게 적혀 있어야 한다.
DEBUG_ONLY_FIELDS: set[tuple[str, str]] = set()

REF_PREFIX = "#/components/schemas/"


def _refs(node: Any) -> set[str]:
    if isinstance(node, dict):
        found = {node["$ref"].removeprefix(REF_PREFIX)} if "$ref" in node else set()
        return found.union(*(_refs(v) for v in node.values()))
    if isinstance(node, list):
        return set().union(*(_refs(v) for v in node))
    return set()


def response_schemas(spec: dict) -> set[str]:
    """응답 본문에서 $ref로 닿는 컴포넌트 이름 전부(요청 본문에서만 쓰는 모델은 빠진다)."""
    schemas = spec["components"]["schemas"]
    todo = {
        ref
        for operations in spec["paths"].values()
        for operation in operations.values()
        for response in operation.get("responses", {}).values()
        for ref in _refs(response)
    }
    seen: set[str] = set()
    while todo:
        name = todo.pop()
        if name not in seen:
            seen.add(name)
            todo |= _refs(schemas[name]) - seen
    return seen


def test_every_response_schema_requires_all_properties():
    spec = TestClient(create_app(provider=MockProvider(), debug=True)).get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    reachable = response_schemas(spec)
    assert {"SessionView", "ResultView", "ErrorBody", "TraceEntry"} <= reachable
    assert "AnswerRequest" not in reachable

    loose = {}
    for name in sorted(reachable):
        properties = set(schemas[name].get("properties", {}))
        optional = properties - set(schemas[name].get("required", []))
        optional -= {field for model, field in DEBUG_ONLY_FIELDS if model == name}
        if optional:
            loose[name] = sorted(optional)
    assert loose == {}
