"""예외 → 오류 응답. 본문은 언제나 {"detail": "<한국어 문장>"}(ErrorBody)이다.

내부 사정은 응답에 싣지 않는다. 요청 검증 상세와 예상하지 못한 예외는 logging으로만 남긴다.
예상하지 못한 예외는 CatchUnexpectedErrors가 받아 한 번만 로그에 남기고 500으로 끝낸다. Starlette의
Exception 처리기는 응답 뒤 예외를 서버로 다시 올려 서버가 같은 traceback을 또 남기므로 쓰지 않는다.
"""
import logging
from http import HTTPStatus
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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


def request_error_items(errors: Sequence[Any]) -> list[dict[str, Any]]:
    """[순수] 요청 검증 오류에서 개발자에게 필요한 위치·문구·종류만 남긴다(입력값은 싣지 않는다)."""
    return [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in errors]


def _error(status_code: int, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(exc.status_code, http_error_detail(exc.status_code, exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.info("요청 형식 오류 %s %s: %s", request.method, request.url.path, exc.errors())
        if not request.app.state.debug:
            return _error(422, INVALID_REQUEST_MESSAGE)
        content = {"detail": INVALID_REQUEST_MESSAGE, "errors": request_error_items(exc.errors())}
        return JSONResponse(status_code=422, content=content)

    @app.exception_handler(HarnessError)
    async def harness_error(request: Request, exc: HarnessError) -> JSONResponse:
        return _error(422, str(exc))

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return _error(502, PROVIDER_FAILED_MESSAGE)

    @app.exception_handler(GenerationFailed)
    async def generation_failed(request: Request, exc: GenerationFailed) -> JSONResponse:
        return _error(502, GENERATION_FAILED_MESSAGE)

    app.add_middleware(CatchUnexpectedErrors)


class CatchUnexpectedErrors:
    """처리기가 없는 예외를 받아 한 번만 로그에 남기고 500 한국어 본문을 보낸다. 서버로 다시 올리지 않는다.

    응답을 이미 보내기 시작했다면 고칠 수 없으므로 로그 없이 다시 올린다(서버가 한 번 남긴다).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_tracking(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_tracking)
        except Exception as exc:
            if started:
                raise
            logger.error("처리하지 못한 예외 %s %s", scope["method"], scope["path"], exc_info=exc)
            await _error(500, INTERNAL_ERROR_MESSAGE)(scope, receive, send)
