from typing import Annotated

from fastapi import Depends, Request

from app.api.locks import SessionLocks
from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry


def get_registry(request: Request) -> HarnessRegistry:
    return request.app.state.registry


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


def get_locks(request: Request) -> SessionLocks:
    return request.app.state.locks


Registry = Annotated[HarnessRegistry, Depends(get_registry)]
Store = Annotated[SessionStore, Depends(get_store)]
Locks = Annotated[SessionLocks, Depends(get_locks)]
