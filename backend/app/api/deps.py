from typing import Annotated

from fastapi import Depends, Request

from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry


def get_registry(request: Request) -> HarnessRegistry:
    return request.app.state.registry


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


Registry = Annotated[HarnessRegistry, Depends(get_registry)]
Store = Annotated[SessionStore, Depends(get_store)]
