"""재고 API(/api/v1/inventory). 사용자가 화면에서 하는 순서대로 부른다."""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import OTHER_CLIENT_ID, api_client

from app.api.errors import install_error_handlers
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.store import InMemoryInventoryStore
from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/inventory"


def make_app():
    return create_app(provider=MockProvider(), inventories=InMemoryInventoryStore())


def test_create_app_wires_inventory_store_and_locks():
    app = make_app()
    assert isinstance(app.state.inventories, InMemoryInventoryStore)
    assert len(app.state.inventory_locks) == 0


def test_inventory_errors_become_korean_error_bodies():
    app = FastAPI()
    install_error_handlers(app)
    app.state.debug = False

    @app.get("/bad")
    def bad():
        raise InventoryError("규칙 위반 문구")

    @app.get("/missing")
    def missing():
        raise InventoryNotFound("없는 대상 문구")

    client = TestClient(app)
    assert client.get("/bad").status_code == 422
    assert client.get("/bad").json() == {"detail": "규칙 위반 문구"}
    assert client.get("/missing").status_code == 404
    assert client.get("/missing").json() == {"detail": "없는 대상 문구"}
