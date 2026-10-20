"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import assets as assets_api, coaching
from app.api.errors import install_error_handlers
from app.api.locks import SessionLocks
from app.api.responses import install_openapi
from app.config import settings
from app.core.assets import Asset, AssetStore
from app.core.storage import Storage, build_storage, opens_connections
from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider
from app.providers.factory import get_provider
from app.providers.image import ImageProvider, get_image_provider
from app.providers.limit import CallSlots, LimitedImageProvider, LimitedProvider


class _AppAssets:
    """app.state.assets로 넘기는 AssetStore. 저장소가 서버 시작 때 열려도 하네스를 먼저 만들 수 있다."""

    def __init__(self, app: FastAPI) -> None:
        self._app = app

    def put(self, owner_id: str, data: bytes, mime: str) -> str:
        return self._app.state.assets.put(owner_id, data, mime)

    def get(self, asset_id: str) -> Asset | None:
        return self._app.state.assets.get(asset_id)

    def delete(self, asset_id: str) -> None:
        self._app.state.assets.delete(asset_id)


def create_app(
    provider: LLMProvider | None = None,
    store: SessionStore | None = None,
    debug: bool | None = None,
    assets: AssetStore | None = None,
    images: ImageProvider | None = None,
    slots: CallSlots | None = None,
) -> FastAPI:
    slots = slots or CallSlots(settings.ai_max_concurrent_calls, settings.ai_queue_wait_seconds)
    llm = LimitedProvider(
        provider
        or get_provider(
            settings.provider,
            model=settings.claude_model,
            effort=settings.claude_effort,
            stage_models=settings.claude_stage_models,
            stage_efforts=settings.claude_stage_efforts,
        ),
        slots,
    )
    image = LimitedImageProvider(images or get_image_provider(settings.image_provider), slots)

    def open_storage() -> Storage:
        # 세션·이미지 저장소는 한 풀을 나눠 쓰므로 둘을 같이 만든다. 넘겨 받은 쪽은 그것을 쓰고 나머지 반쪽은 버린다.
        return build_storage(
            settings.store,
            settings.database_path,
            settings.asset_dir,
            settings.database_url.get_secret_value() if settings.database_url else None,
        )

    def attach(storage: Storage | None) -> None:
        app.state.store = store or storage.sessions
        app.state.assets = assets or storage.assets

    needs_storage = store is None or assets is None
    # 연결 풀 같은 자원이 필요한 저장소는 서버가 시작할 때(lifespan) 열고 끝날 때 닫는다. import만으로는 열지 않는다.
    deferred = needs_storage and opens_connections(settings.store)
    built: Storage | None = None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        nonlocal built
        if deferred:
            built = open_storage()
            attach(built)
        try:
            yield
        finally:
            if built:
                built.close()

    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
        lifespan=lifespan,
    )
    if needs_storage and not deferred:
        built = open_storage()
    if not deferred:
        attach(built)
    # 하네스는 만들 때 이미지 저장소를 받으므로, 저장소가 늦게 열려도 되게 앱 상태를 거쳐 부른다
    app.state.registry = HarnessRegistry(llm, image, _AppAssets(app))
    app.state.locks = SessionLocks()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)
    app.include_router(assets_api.router)
    install_error_handlers(app)
    install_openapi(app)
    return app


app = create_app()
