"""재고 API(/api/v1/inventory). 사용자가 화면에서 하는 순서대로 부른다."""
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import OTHER_CLIENT_ID, api_client

from app.api.errors import install_error_handlers
from app.core.messages import (
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
)
from app.inventory import service
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import InventorySettings, ReorderPolicy
from app.inventory.store import InMemoryInventoryStore
from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/inventory"
POLICY = {"min_stock": "1", "target_stock": "1", "purchase_unit": "1", "lead_days": 1, "unit_price": "0"}


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



@pytest.fixture
def client():
    return api_client(make_app())


def _bulk(client, *rows):
    return client.post(f"{BASE}/items/bulk", json={"items": list(rows)})


def _ids(view):
    return [row["item"]["item_id"] for row in view["items"]]


def test_empty_inventory_for_new_owner(client):
    response = client.get(BASE)
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "suppliers": [],
        "settings": {"address": "", "anomaly_drop_ratio": "0.5", "stale_days": 7},
        "last_close": None,
    }


def test_owner_header_is_required():
    assert api_client(make_app(), client_id=None).get(BASE).status_code == 422


def test_register_policy_close_and_see_shortage(client):
    supplier = client.post(f"{BASE}/suppliers", json={"name": "원단상회"}).json()["suppliers"][0]
    view = _bulk(
        client,
        {"name": "원단", "kind": "material", "unit": "m", "procurement": "purchase", "supplier_id": supplier["supplier_id"], "quantity": "20"},
        {"name": "에코백", "kind": "finished", "unit": "개", "procurement": "make"},
    )
    assert view.status_code == 201
    fabric, bag = _ids(view.json())

    policy = {"min_stock": "10", "target_stock": "30", "purchase_unit": "5", "lead_days": 3, "unit_price": "4000"}
    assert client.put(f"{BASE}/items/{fabric}/policy", json=policy).status_code == 200

    check = client.post(f"{BASE}/closes/check", json={"counts": {fabric: "8"}}).json()
    assert [(a["item_id"], a["kind"]) for a in check["anomalies"]] == [(fabric, "drop")]  # 20 → 8 은 60% 감소

    closed = client.post(f"{BASE}/closes", json={"close_date": "2026-11-08", "counts": {fabric: "8"}, "confirmed": [fabric]})
    assert closed.status_code == 201
    body = closed.json()
    assert body["close"]["counts"] == {fabric: "8"}
    rows = {row["item"]["item_id"]: row for row in body["inventory"]["items"]}
    assert rows[fabric]["status"] == "short"
    assert D(rows[fabric]["suggested_quantity"]) == D(25)  # 30 − 8 = 22 → 5 단위로 올림
    assert rows[bag]["status"] == "uncounted"
    assert body["inventory"]["last_close"]["close_id"] == body["close"]["close_id"]


def test_rule_violations_are_422_and_change_nothing(client):
    fabric = _ids(_bulk(client, {"name": "원단", "kind": "material", "unit": "m", "quantity": "20"}).json())[0]
    before = client.get(BASE).json()

    unconfirmed = client.post(f"{BASE}/closes", json={"close_date": "2026-11-08", "counts": {fabric: "1"}})
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["detail"].startswith("확인이 필요한 수량이 있습니다")
    assert client.patch(f"{BASE}/items/{fabric}", json={"unit": "cm"}).status_code == 422
    bad_policy = {"min_stock": "10", "target_stock": "5", "purchase_unit": "1", "lead_days": 1, "unit_price": "0"}
    assert client.put(f"{BASE}/items/{fabric}/policy", json=bad_policy).status_code == 422
    assert _bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).status_code == 422  # 같은 품목

    assert client.get(BASE).json() == before


def test_unknown_ids_are_404(client):
    item_missing = {"detail": INVENTORY_ITEM_NOT_FOUND_MESSAGE}
    patched = client.patch(f"{BASE}/items/it_none", json={"name": "x"})
    assert (patched.status_code, patched.json()) == (404, item_missing)
    supplier = client.patch(f"{BASE}/suppliers/sup_none", json={"name": "x"})
    assert (supplier.status_code, supplier.json()) == (404, {"detail": INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE})
    put = client.put(f"{BASE}/items/it_none/policy", json=POLICY)
    assert (put.status_code, put.json()) == (404, item_missing)


def test_other_owner_sees_nothing_and_cannot_touch(client):
    fabric = _ids(_bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).json())[0]
    supplier_id = client.post(f"{BASE}/suppliers", json={"name": "상회"}).json()["suppliers"][0]["supplier_id"]
    other = api_client(client.app, client_id=OTHER_CLIENT_ID)
    item_missing = {"detail": INVENTORY_ITEM_NOT_FOUND_MESSAGE}

    assert other.get(BASE).json()["items"] == []
    patched = other.patch(f"{BASE}/items/{fabric}", json={"name": "남의 것"})
    assert (patched.status_code, patched.json()) == (404, item_missing)
    put = other.put(f"{BASE}/items/{fabric}/policy", json=POLICY)
    assert (put.status_code, put.json()) == (404, item_missing)
    supplier = other.patch(f"{BASE}/suppliers/{supplier_id}", json={"name": "남의 상회"})
    assert (supplier.status_code, supplier.json()) == (404, {"detail": INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE})
    closed = other.post(f"{BASE}/closes", json={"close_date": "2026-11-08", "counts": {fabric: "1"}})
    assert (closed.status_code, closed.json()) == (422, {"detail": INVENTORY_UNKNOWN_ITEM_MESSAGE})
    assert client.get(BASE).json()["items"][0]["item"]["name"] == "원단"
    assert client.get(BASE).json()["suppliers"][0]["name"] == "상회"
    assert client.get(BASE).json()["items"][0]["policy"] is None


def test_settings_and_supplier_patch(client):
    settings = {"address": "서울시 어딘가 1", "anomaly_drop_ratio": "0.3", "stale_days": 5}
    assert client.put(f"{BASE}/settings", json=settings).json()["settings"] == settings
    supplier_id = client.post(f"{BASE}/suppliers", json={"name": "상회"}).json()["suppliers"][0]["supplier_id"]
    patched = client.patch(f"{BASE}/suppliers/{supplier_id}", json={"mock_outcome": "out_of_stock"}).json()
    assert patched["suppliers"][0] == {"supplier_id": supplier_id, "name": "상회", "kind": "mock", "mock_outcome": "out_of_stock"}


def test_single_item_create_and_archive(client):
    created = client.post(f"{BASE}/items", json={"name": "끈", "kind": "packaging", "unit": "개"})
    assert created.status_code == 201
    item_id = _ids(created.json())[0]
    archived = client.patch(f"{BASE}/items/{item_id}", json={"archived": True}).json()
    assert archived["items"][0]["item"]["archived"] is True


def test_mutations_hold_the_owner_lock(monkeypatch):
    app = make_app()
    client = api_client(app)
    seen = []
    original = service.add_supplier

    def spy(state, draft):
        seen.append(app.state.inventory_locks.is_held(state.owner_id))
        return original(state, draft)

    monkeypatch.setattr(service, "add_supplier", spy)
    client.post(f"{BASE}/suppliers", json={"name": "상회"})
    assert seen == [True]


def test_exponent_numbers_come_back_plain(client):
    fabric = _ids(_bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).json())[0]
    put = client.put(f"{BASE}/items/{fabric}/policy", json=POLICY | {"unit_price": "1e3"})
    assert put.json()["items"][0]["policy"]["unit_price"] == "1000"


def test_state_holds_base_types_not_request_subclasses():
    app = make_app()
    client = api_client(app)
    owner = client.headers["X-Client-Id"]
    fabric = _ids(_bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).json())[0]
    client.put(f"{BASE}/settings", json={"address": "", "anomaly_drop_ratio": "0.5", "stale_days": 7})
    client.put(f"{BASE}/items/{fabric}/policy", json=POLICY)

    state = app.state.inventories.get(owner)
    assert type(state.settings) is InventorySettings
    assert type(state.policies[fabric]) is ReorderPolicy


def test_create_app_without_inventories_uses_storage():
    app = create_app(provider=MockProvider())
    assert isinstance(app.state.inventories, InMemoryInventoryStore)
    client = api_client(app)
    assert client.get(BASE).json()["items"] == []
    assert _bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).status_code == 201
