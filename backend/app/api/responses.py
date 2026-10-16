"""OpenAPI 오류 응답 선언. 경로마다 실제로 낼 수 있는 오류만 적는다.

500(예상하지 못한 오류)은 어느 경로에서나 날 수 있어 라우터 공통으로 둔다. FastAPI는 경로 매개변수가
있으면 기본 422(HTTPValidationError)를 끼워 넣는데, 문자열 경로 매개변수는 검증에 실패할 일이 없고
런타임 422 본문도 ErrorBody이므로 strip_default_validation_errors로 걷어 낸다.
"""
from typing import Any

from fastapi import FastAPI

from app.schemas.coaching import ErrorBody, RequestErrorBody

_DESCRIPTIONS = {
    404: "과제·세션·결과가 없음",
    422: "요청 형식(사용자 식별 헤더 포함)이나 답변이 규칙에 맞지 않음",
    500: "예상하지 못한 서버 오류",
    502: "AI 호출 또는 결과 생성 실패",
}

_DEFAULT_422_REF = "#/components/schemas/HTTPValidationError"


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """[순수] 라우트 데코레이터의 responses 값. 예: error_responses(404, 422, 502)."""
    return {
        status: {
            "model": RequestErrorBody if status == 422 else ErrorBody,
            "description": _DESCRIPTIONS[status],
        }
        for status in statuses
    }


def strip_default_validation_errors(schema: dict[str, Any]) -> None:
    """FastAPI가 자동으로 넣은 422(HTTPValidationError)와 그 스키마를 OpenAPI 문서에서 지운다."""
    for operations in schema.get("paths", {}).values():
        for operation in operations.values():
            response = operation.get("responses", {}).get("422", {})
            ref = response.get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
            if ref == _DEFAULT_422_REF:
                del operation["responses"]["422"]
    components = schema.get("components", {}).get("schemas", {})
    for name in ("HTTPValidationError", "ValidationError"):
        components.pop(name, None)


def install_openapi(app: FastAPI) -> None:
    default_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            strip_default_validation_errors(default_openapi())
        return app.openapi_schema  # type: ignore[return-value]

    app.openapi = openapi  # type: ignore[method-assign]
