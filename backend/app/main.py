"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import assets as assets_api, coaching, inventory as inventory_api
from app.api.errors import install_error_handlers
from app.api.locks import SessionLocks
from app.api.responses import install_openapi
from app.config import provider_options, settings
from app.core.assets import AssetStore
from app.core.storage import build_storage
from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry
from app.inventory.store import InventoryStore
from app.inventory.supplier import SupplierProvider, get_supplier_provider
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
    inventories: InventoryStore | None = None,
    supplier: SupplierProvider | None = None,
) -> FastAPI:
    slots = slots or CallSlots(settings.ai_max_concurrent_calls, settings.ai_queue_wait_seconds)
    llm = LimitedProvider(
        provider
        or get_provider(settings.provider, **provider_options(settings)),
        slots,
    )
    image = LimitedImageProvider(images or get_image_provider(settings.image_provider), slots)

    storage = None
    # 하나라도 빠지면 저장소 묶음 전체를 만든다(`inventories`만 빼는 것은 테스트용: 세션·이미지 저장소도 새로 만들어진다).
    if store is None or assets is None or inventories is None:  # 연결은 만들 때가 아니라 서버가 시작할 때(lifespan) 한다
        storage = build_storage(
            settings.store,
            settings.database_path,
            settings.asset_dir,
            settings.database_url.get_secret_value() if settings.database_url else None,
        )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if storage:
            storage.open()
        try:
            yield
        finally:
            if storage:
                storage.close()

    debug_on = settings.debug if debug is None else debug
    # 배포(DEBUG=false)에서는 API 문서를 닫는다. 프론트 타입 생성은 HTTP가 아니라 app.openapi()로 뽑으므로 영향이 없다.
    docs = {} if debug_on else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
        lifespan=lifespan,
        **docs,
    )
    app.state.store = store or storage.sessions
    app.state.assets = assets or storage.assets
    app.state.registry = HarnessRegistry(llm, image, app.state.assets)
    app.state.llm = llm  # 재고 AI 기준 추천(app/inventory/advisor.py)이 코칭과 같은 호출 상한을 쓴다
    app.state.supplier = supplier or get_supplier_provider(settings.supplier)
    app.state.locks = SessionLocks()
    app.state.inventories = inventories or storage.inventories
    app.state.inventory_locks = SessionLocks()  # 키는 owner id: 서로 다른 client id 수만큼만 늘고, 실패한 요청도 잠금을 만들 수 있다
    app.state.debug = debug_on
    app.include_router(coaching.router)
    app.include_router(assets_api.router)
    app.include_router(inventory_api.router)
    install_error_handlers(app)
    install_openapi(app)
    return app


app = create_app()
