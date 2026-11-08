"""재고 API(/api/v1/inventory). 사용자가 화면에서 하는 순서대로 부른다."""
from decimal import Decimal as D

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import OTHER_CLIENT_ID, api_client

from app.api.errors import install_error_handlers
from app.core.messages import (
    INVENTORY_HOLD_NOT_FOUND_MESSAGE,
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_ORDER_NOT_FOUND_MESSAGE,
    INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
    PROVIDER_FAILED_MESSAGE,
)
from app.inventory import service
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import InventorySettings, ReorderPolicy
from app.inventory.store import InMemoryInventoryStore
from app.main import create_app
from app.providers.mock import MockProvider
from app.inventory.supplier import MockSupplier

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
        "orders": [],
        "holds": [],
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


def _shop(client, outcome="accept"):
    client.put(f"{BASE}/settings", json={"address": "서울시 어딘가 1", "anomaly_drop_ratio": "0.5", "stale_days": 7})
    supplier_id = client.post(f"{BASE}/suppliers", json={"name": "원단상회", "mock_outcome": outcome}).json()["suppliers"][0]["supplier_id"]
    view = _bulk(client, {"name": "원단", "kind": "material", "unit": "m", "procurement": "purchase", "supplier_id": supplier_id, "quantity": "10"})
    item = _ids(view.json())[0]
    policy = {"min_stock": "20", "target_stock": "50", "purchase_unit": "10", "lead_days": 3, "unit_price": "1000"}
    client.put(f"{BASE}/items/{item}/policy", json=policy)
    return item


def _row(view, item):
    return next(r for r in view["items"] if r["item"]["item_id"] == item)


def test_manual_order_partial_receipt_and_idempotency(client):
    item = _shop(client)
    body = {"request_id": "req-00000001", "lines": [{"item_id": item, "quantity": "40"}]}

    placed = client.post(f"{BASE}/orders", json=body)
    assert placed.status_code == 201
    order = placed.json()["order"]
    assert order["status"] == "accepted" and D(order["total"]) == D(40000)
    assert D(_row(placed.json()["inventory"], item)["in_transit"]) == D(40)
    assert _row(placed.json()["inventory"], item)["status"] == "in_transit"

    again = client.post(f"{BASE}/orders", json=body).json()
    assert again["order"]["order_id"] == order["order_id"]
    assert len(again["inventory"]["orders"]) == 1

    received = client.post(f"{BASE}/orders/{order['order_id']}/receipts", json={"lines": [{"item_id": item, "quantity": "15"}]})
    assert received.status_code == 200
    assert received.json()["order"]["status"] == "partially_received"
    row = _row(received.json()["inventory"], item)
    assert (D(row["on_hand"]), D(row["in_transit"])) == (D(25), D(25))

    over = client.post(f"{BASE}/orders/{order['order_id']}/receipts", json={"lines": [{"item_id": item, "quantity": "26"}]})
    assert over.status_code == 422


def test_unknown_order_refresh_resolves_hold(client):
    item = _shop(client, "unknown_then_accept")
    placed = client.post(f"{BASE}/orders", json={"request_id": "req-00000002", "lines": [{"item_id": item, "quantity": "40"}]}).json()
    assert placed["order"]["status"] == "unknown"
    assert [(h["reason"], h["resolved"]) for h in placed["inventory"]["holds"]] == [("unknown", False)]

    refreshed = client.post(f"{BASE}/orders/{placed['order']['order_id']}/refresh").json()
    assert refreshed["order"]["status"] == "accepted"
    assert [h["resolved"] for h in refreshed["inventory"]["holds"]] == [True]


def test_hold_resolve_and_404s(client):
    item = _shop(client, "out_of_stock")
    placed = client.post(f"{BASE}/orders", json={"request_id": "req-00000003", "lines": [{"item_id": item, "quantity": "40"}]}).json()
    hold_id = placed["inventory"]["holds"][0]["hold_id"]

    resolved = client.post(f"{BASE}/holds/{hold_id}/resolve")
    assert resolved.status_code == 200 and resolved.json()["holds"][0]["resolved"] is True
    assert client.post(f"{BASE}/holds/ho_none/resolve").json() == {"detail": INVENTORY_HOLD_NOT_FOUND_MESSAGE}
    assert client.post(f"{BASE}/orders/or_none/refresh").json() == {"detail": INVENTORY_ORDER_NOT_FOUND_MESSAGE}
    missing = client.post(f"{BASE}/orders/or_none/receipts", json={"lines": [{"item_id": item, "quantity": "1"}]})
    assert missing.status_code == 404


def test_auto_order_runs_after_close_once(client):
    item = _shop(client)
    on = {"enabled": True, "consent": True, "per_order_limit": "100000", "monthly_limit": "500000"}
    view = client.put(f"{BASE}/items/{item}/auto-order", json=on)
    assert view.status_code == 200 and _row(view.json(), item)["auto_order"]["enabled"] is True
    assert client.put(f"{BASE}/items/{item}/auto-order", json=on | {"consent": False}).status_code == 422

    closed = client.post(f"{BASE}/closes", json={"close_date": "2026-11-08", "counts": {item: "5"}, "confirmed": [item]}).json()
    [outcome] = closed["auto_orders"]
    assert outcome["item_id"] == item and outcome["status"] == "accepted" and outcome["hold_reason"] is None
    [order] = closed["inventory"]["orders"]
    assert order["origin"] == "auto" and D(order["lines"][0]["quantity"]) == D(50)

    second = client.post(f"{BASE}/closes", json={"close_date": "2026-11-08", "counts": {item: "5"}}).json()
    assert second["auto_orders"] == []  # 배송 중이라 부족이 아니다
    assert len(second["inventory"]["orders"]) == 1


def test_policy_suggestion_and_apply(client):
    item = _shop(client)
    assert client.post(f"{BASE}/items/{item}/policy/suggestion/apply").json() == {"detail": INVENTORY_SUGGESTION_NOT_FOUND_MESSAGE}

    suggested = client.post(f"{BASE}/items/{item}/policy/suggestion")
    assert suggested.status_code == 200
    row = _row(suggested.json(), item)
    assert row["suggestion"]["reason"] and D(row["policy"]["min_stock"]) == D(20)

    applied = _row(client.post(f"{BASE}/items/{item}/policy/suggestion/apply").json(), item)
    assert applied["suggestion"] is None
    assert D(applied["policy"]["min_stock"]) == D(row["suggestion"]["min_stock"])
    assert D(applied["policy"]["unit_price"]) == D(1000)


def test_policy_suggestion_provider_failure_is_502_and_changes_nothing():
    app = create_app(provider=MockProvider(fail_stages={"inventory_policy"}), inventories=InMemoryInventoryStore())
    client = api_client(app)
    item = _shop(client)
    before = client.get(BASE).json()
    failed = client.post(f"{BASE}/items/{item}/policy/suggestion")
    assert failed.status_code == 502 and failed.json() == {"detail": PROVIDER_FAILED_MESSAGE}
    assert client.get(BASE).json() == before


def test_other_owner_cannot_touch_orders_or_holds(client):
    item = _shop(client, "out_of_stock")
    placed = client.post(f"{BASE}/orders", json={"request_id": "req-00000004", "lines": [{"item_id": item, "quantity": "40"}]}).json()
    other = api_client(client.app, client_id=OTHER_CLIENT_ID)
    assert other.post(f"{BASE}/orders/{placed['order']['order_id']}/refresh").status_code == 404
    assert other.post(f"{BASE}/holds/{placed['inventory']['holds'][0]['hold_id']}/resolve").status_code == 404
    assert other.post(f"{BASE}/orders", json={"request_id": "req-00000004", "lines": [{"item_id": item, "quantity": "1"}]}).status_code == 422


def test_order_routes_use_injected_supplier():
    class Counting(MockSupplier):
        calls = 0

        def place(self, *args):
            Counting.calls += 1
            return super().place(*args)

    app = create_app(provider=MockProvider(), inventories=InMemoryInventoryStore(), supplier=Counting())
    client = api_client(app)
    item = _shop(client)
    client.post(f"{BASE}/orders", json={"request_id": "req-00000005", "lines": [{"item_id": item, "quantity": "10"}]})
    assert Counting.calls == 1
