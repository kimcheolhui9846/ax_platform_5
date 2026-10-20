"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import assets as assets_api, coaching
from app.api.errors import install_error_handlers
from app.api.locks import SessionLocks
from app.api.responses import install_openapi
from app.config import settings
from app.core.assets import AssetStore
from app.core.storage import build_storage
from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider
from app.providers.factory import get_provider
from app.providers.image import ImageProvider, get_image_provider
from app.providers.limit import CallSlots, LimitedImageProvider, LimitedProvider


def create_app(
    provider: LLMProvider | None = None,
    store: SessionStore | None = None,
    debug: bool | None = None,
    assets: AssetStore | None = None,
    images: ImageProvider | None = None,
    slots: CallSlots | None = None,
) -> FastAPI:
    built = None
    if store is None or assets is None:  # 넘겨 받지 않은 쪽만 설정(STORE)대로 만든다
        built = build_storage(
            settings.store,
            settings.database_path,
            settings.asset_dir,
            settings.database_url.get_secret_value() if settings.database_url else None,
        )
    close_storage = built.close if built else (lambda: None)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            close_storage()

    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.store = store or built.sessions
    app.state.assets = assets or built.assets
    slots = slots or CallSlots(settings.ai_max_concurrent_calls, settings.ai_queue_wait_seconds)
    app.state.registry = HarnessRegistry(
        LimitedProvider(
            provider
            or get_provider(
                settings.provider,
                model=settings.claude_model,
                effort=settings.claude_effort,
                stage_models=settings.claude_stage_models,
                stage_efforts=settings.claude_stage_efforts,
            ),
            slots,
        ),
        LimitedImageProvider(images or get_image_provider(settings.image_provider), slots),
        app.state.assets,
    )
    app.state.locks = SessionLocks()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)
    app.include_router(assets_api.router)
    install_error_handlers(app)
    install_openapi(app)
    return app


app = create_app()
