"""예외 → 오류 응답. 본문은 언제나 {"detail": "<한국어 문장>"}(ErrorBody)이다.

내부 사정은 응답에 싣지 않는다. 요청 검증 상세와 예상하지 못한 예외는 logging으로만 남긴다.
"""
import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.messages import (
    GENERATION_FAILED_MESSAGE,
    HTTP_ERROR_FALLBACK_MESSAGE,
    HTTP_STATUS_MESSAGES,
    INTERNAL_ERROR_MESSAGE,
    INVALID_REQUEST_MESSAGE,
    PROVIDER_FAILED_MESSAGE,
)
from app.harness.errors import GenerationFailed, HarnessError
from app.providers.base import ProviderError

logger = logging.getLogger(__name__)


def http_error_detail(status_code: int, detail: Any) -> str:
    """[순수] 라우터가 정한 한국어 detail은 그대로 두고, Starlette 기본 문구(영어 상태명)는 한국어로 바꾼다."""
    try:
        default = HTTPStatus(status_code).phrase
    except ValueError:
        default = None
    if isinstance(detail, str) and detail and detail != default:
        return detail
    return HTTP_STATUS_MESSAGES.get(status_code, HTTP_ERROR_FALLBACK_MESSAGE)


def _error(status_code: int, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, http_error_detail(exc.status_code, exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("요청 형식 오류 %s %s: %s", request.method, request.url.path, exc.errors())
        return _error(422, INVALID_REQUEST_MESSAGE)

    @app.exception_handler(HarnessError)
    async def harness_error(request: Request, exc: HarnessError) -> JSONResponse:
        return _error(422, str(exc))

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return _error(502, PROVIDER_FAILED_MESSAGE)

    @app.exception_handler(GenerationFailed)
    async def generation_failed(request: Request, exc: GenerationFailed) -> JSONResponse:
        return _error(502, GENERATION_FAILED_MESSAGE)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # Starlette는 이 응답을 보낸 뒤 예외를 서버로 다시 올린다(서버 로그에도 남는다).
        logger.error("처리하지 못한 예외 %s %s", request.method, request.url.path, exc_info=exc)
        return _error(500, INTERNAL_ERROR_MESSAGE)
