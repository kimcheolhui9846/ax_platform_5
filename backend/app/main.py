"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from fastapi import FastAPI

from app.api import assets as assets_api, coaching
from app.api.errors import install_error_handlers
from app.api.locks import SessionLocks
from app.api.responses import install_openapi
from app.config import settings
from app.core.assets import AssetStore, build_asset_store
from app.core.store import SessionStore, build_store
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider
from app.providers.factory import get_provider
from app.providers.image import ImageProvider, get_image_provider


def create_app(
    provider: LLMProvider | None = None,
    store: SessionStore | None = None,
    debug: bool | None = None,
    assets: AssetStore | None = None,
    images: ImageProvider | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
    )
    app.state.store = store or build_store(settings.store, settings.database_path)
    app.state.assets = assets or build_asset_store(settings.store, settings.asset_dir)
    app.state.registry = HarnessRegistry(
        provider
        or get_provider(
            settings.provider,
            model=settings.claude_model,
            effort=settings.claude_effort,
            stage_models=settings.claude_stage_models,
            stage_efforts=settings.claude_stage_efforts,
        ),
        images or get_image_provider(settings.image_provider),
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
