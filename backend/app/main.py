"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import coaching
from app.config import settings
from app.core.store import InMemorySessionStore, SessionStore
from app.harness.errors import HarnessError
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
        separate_input_output_schemas=False,
    )
    app.state.registry = HarnessRegistry(provider or get_provider(settings.provider))
    app.state.store = store or InMemorySessionStore()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)

    @app.exception_handler(HarnessError)
    async def harness_error(request: Request, exc: HarnessError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": "AI 호출에 실패했습니다. 다시 시도해 주세요."},
        )

    return app


app = create_app()
