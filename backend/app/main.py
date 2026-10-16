"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import coaching
from app.config import settings
from app.core.messages import (
    GENERATION_FAILED_MESSAGE,
    INVALID_REQUEST_MESSAGE,
    PROVIDER_FAILED_MESSAGE,
)
from app.core.store import InMemorySessionStore, SessionStore
from app.harness.errors import GenerationFailed, HarnessError
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider, ProviderError
from app.providers.factory import get_provider


def create_app(
    provider: LLMProvider | None = None,
    store: SessionStore | None = None,
    debug: bool | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
    )
    app.state.registry = HarnessRegistry(provider or get_provider(settings.provider))
    app.state.store = store or InMemorySessionStore()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)

    @app.exception_handler(RequestValidationError)
    async def request_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": INVALID_REQUEST_MESSAGE})

    @app.exception_handler(HarnessError)
    async def harness_error(request: Request, exc: HarnessError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": PROVIDER_FAILED_MESSAGE})

    @app.exception_handler(GenerationFailed)
    async def generation_failed(request: Request, exc: GenerationFailed) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": GENERATION_FAILED_MESSAGE})

    return app


app = create_app()
