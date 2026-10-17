from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app.api.locks import SessionLocks
from app.api.owner import current_owner
from app.core.assets import AssetStore
from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry


def get_registry(request: Request) -> HarnessRegistry:
    return request.app.state.registry


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


def get_locks(request: Request) -> SessionLocks:
    return request.app.state.locks


def get_assets(request: Request) -> AssetStore:
    return request.app.state.assets


Registry = Annotated[HarnessRegistry, Depends(get_registry)]
Store = Annotated[SessionStore, Depends(get_store)]
Locks = Annotated[SessionLocks, Depends(get_locks)]
Assets = Annotated[AssetStore, Depends(get_assets)]


def require_debug(request: Request) -> None:
    """DEBUG가 아니면 없는 경로와 같은 404. 라우트 dependencies에 두면 owner 검사보다 먼저 돈다."""
    if not request.app.state.debug:
        raise HTTPException(status_code=404)


Owner = Annotated[str, Depends(current_owner)]
