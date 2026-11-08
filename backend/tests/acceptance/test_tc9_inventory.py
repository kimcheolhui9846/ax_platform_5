"""TC9 재고 관리(주문·입고·자동 주문): 사용자가 재고 API로 하는 순서를 그대로 따라간다. 거래처는 Mock이다."""
from decimal import Decimal as D

import pytest

from app.inventory.store import InMemoryInventoryStore
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/inventory"
ADDRESS = "서울시 어딘가 1"
POLICY = {"min_stock": "20", "target_stock": "50", "purchase_unit": "10", "lead_days": 3, "unit_price": "1000"}
AUTO_ON = {"enabled": True, "consent": True, "per_order_limit": "100000", "monthly_limit": "500000"}
CLOSE_DAY = "2026-11-08"


@pytest.fixture
def client():
    return api_client(create_app(provider=MockProvider(), inventories=InMemoryInventoryStore()))


def set_address(client):
    client.put(f"{BASE}/settings", json={"address": ADDRESS, "anomaly_drop_ratio": "0.5", "stale_days": 7})


def add_supplier(client, name="원단상회", outcome="accept") -> str:
    view = client.post(f"{BASE}/suppliers", json={"name": name, "mock_outcome": outcome}).json()
    return next(s["supplier_id"] for s in view["suppliers"] if s["name"] == name)


def add_item(client, name, supplier_id, quantity="10", policy=POLICY) -> str:
    row = {"name": name, "kind": "material", "unit": "m", "procurement": "purchase", "supplier_id": supplier_id}
    if quantity is not None:
        row["quantity"] = quantity
    view = client.post(f"{BASE}/items/bulk", json={"items": [row]}).json()
    item_id = next(r["item"]["item_id"] for r in view["items"] if r["item"]["name"] == name)
    assert client.put(f"{BASE}/items/{item_id}/policy", json=policy).status_code == 200
    return item_id


def row_of(view, item_id):
    return next(r for r in view["items"] if r["item"]["item_id"] == item_id)


def close(client, counts, confirmed=()):
    response = client.post(f"{BASE}/closes", json={"close_date": CLOSE_DAY, "counts": counts, "confirmed": list(confirmed)})
    assert response.status_code == 201
    return response.json()


def order(client, request_id, item_id, quantity="40", **line):
    return client.post(f"{BASE}/orders", json={"request_id": request_id, "lines": [{"item_id": item_id, "quantity": quantity, **line}]})


def test_tc9_1_등록_마감_부족과_미입력(client):
    set_address(client)
    supplier = add_supplier(client)
    counted = add_item(client, "원단", supplier, quantity="10")
    untouched = add_item(client, "단추", supplier, quantity=None)

    closed = close(client, {counted: "5"}, confirmed=[counted])

    short = row_of(closed["inventory"], counted)
    assert (short["status"], D(short["on_hand"]), D(short["suggested_quantity"])) == ("short", D(5), D(50))
    missing = row_of(closed["inventory"], untouched)
    assert missing["status"] == "uncounted" and missing["on_hand"] is None


def test_tc9_2_수동_주문은_같은_request_id로_두_번_보내도_한_번만(client):
    set_address(client)
    item = add_item(client, "원단", add_supplier(client))

    placed = order(client, "req-tc900002", item).json()

    assert placed["order"]["status"] == "accepted"
    assert D(row_of(placed["inventory"], item)["in_transit"]) == D(40)
    again = order(client, "req-tc900002", item).json()
    assert again["order"]["order_id"] == placed["order"]["order_id"]
    assert len(again["inventory"]["orders"]) == 1


def test_tc9_3_일부_입고와_이미_마감에서_셌어요(client):
    set_address(client)
    item = add_item(client, "원단", add_supplier(client))
    placed = order(client, "req-tc900003", item).json()["order"]
    receipts = f"{BASE}/orders/{placed['order_id']}/receipts"

    partial = client.post(receipts, json={"lines": [{"item_id": item, "quantity": "15"}]}).json()
    assert partial["order"]["status"] == "partially_received"
    assert D(row_of(partial["inventory"], item)["on_hand"]) == D(25)

    over = client.post(receipts, json={"lines": [{"item_id": item, "quantity": "26"}]})
    assert over.status_code == 422

    counted = client.post(receipts, json={"lines": [{"item_id": item, "quantity": "25", "already_counted": True}]}).json()
    assert counted["order"]["status"] == "received"
    assert D(row_of(counted["inventory"], item)["on_hand"]) == D(25)


def test_tc9_4_자동_주문은_마감_직후_한_번이고_접수_불명은_다시_주문하지_않고_보류(client):
    set_address(client)
    fine = add_item(client, "원단", add_supplier(client))
    unsure = add_item(client, "단추", add_supplier(client, "단추상회", "unknown_then_accept"))
    for item in (fine, unsure):
        assert client.put(f"{BASE}/items/{item}/auto-order", json=AUTO_ON).status_code == 200

    closed = close(client, {fine: "5", unsure: "5"}, confirmed=[fine, unsure])

    outcomes = {o["item_id"]: o for o in closed["auto_orders"]}
    assert (outcomes[fine]["status"], outcomes[fine]["hold_reason"]) == ("accepted", None)
    assert (outcomes[unsure]["status"], outcomes[unsure]["hold_reason"]) == ("unknown", "unknown")
    assert [(h["item_id"], h["reason"], h["resolved"]) for h in closed["inventory"]["holds"]] == [(unsure, "unknown", False)]
    assert len(closed["inventory"]["orders"]) == 2

    again = close(client, {fine: "5", unsure: "5"})
    assert [o["status"] for o in again["inventory"]["orders"]].count("unknown") == 1
    assert len(again["inventory"]["orders"]) == 2


def test_tc9_5_보류_재조회와_해결(client):
    set_address(client)
    unsure_supplier = add_supplier(client, "단추상회", "unknown_then_accept")
    unsure = add_item(client, "단추", unsure_supplier)
    placed = order(client, "req-tc900051", unsure, "10").json()
    assert placed["order"]["status"] == "unknown"
    assert [h["resolved"] for h in placed["inventory"]["holds"]] == [False]

    refreshed = client.post(f"{BASE}/orders/{placed['order']['order_id']}/refresh").json()
    assert refreshed["order"]["status"] == "accepted"
    assert [h["resolved"] for h in refreshed["inventory"]["holds"]] == [True]

    pricey_supplier = add_supplier(client, "원단상회", "price_changed")
    pricey = add_item(client, "원단", pricey_supplier)
    rejected = order(client, "req-tc900052", pricey).json()
    assert rejected["order"]["status"] == "rejected" and rejected["order"]["reject_reason"] == "price_changed"
    [hold] = [h for h in rejected["inventory"]["holds"] if h["item_id"] == pricey]
    assert hold["reason"] == "price_changed" and hold["current_unit_price"] is not None

    client.patch(f"{BASE}/suppliers/{pricey_supplier}", json={"mock_outcome": "accept"})
    retried = order(client, "req-tc900053", pricey, unit_price=hold["current_unit_price"]).json()
    assert retried["order"]["status"] == "accepted"
    assert D(retried["order"]["lines"][0]["unit_price"]) == D(hold["current_unit_price"])
    resolved = client.post(f"{BASE}/holds/{hold['hold_id']}/resolve").json()
    assert [h for h in resolved["holds"] if not h["resolved"]] == []


def test_tc9_6_한도를_넘는_자동_주문은_줄이지_않고_보류(client):
    set_address(client)
    item = add_item(client, "원단", add_supplier(client))
    limited = AUTO_ON | {"per_order_limit": "1"}
    assert client.put(f"{BASE}/items/{item}/auto-order", json=limited).status_code == 200

    closed = close(client, {item: "5"}, confirmed=[item])

    [outcome] = closed["auto_orders"]
    assert (outcome["order_id"], outcome["status"], outcome["hold_reason"]) == (None, None, "limit_exceeded")
    assert closed["inventory"]["orders"] == []
    assert [h["reason"] for h in closed["inventory"]["holds"]] == ["limit_exceeded"]
