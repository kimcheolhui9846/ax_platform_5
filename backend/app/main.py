"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from fastapi import FastAPI

from app.api import coaching
from app.api.errors import install_error_handlers
from app.api.locks import SessionLocks
from app.api.responses import install_openapi
from app.config import settings
from app.core.store import InMemorySessionStore, SessionStore
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider
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
    app.state.locks = SessionLocks()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)
    install_error_handlers(app)
    install_openapi(app)
    return app


app = create_app()
