# 재고 관리 핵심(PR #40) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** owner마다 재고 묶음 하나를 두고 품목·거래처·설정·보충 기준·하루 마감을 API로 다룬다. 수량·상태·제안 주문량·이상 수량은 원장에서 순수 함수로 계산한다.

**Architecture:** 새 패키지 `backend/app/inventory/`에 저장 모델(`models.py`), 순수 계산(`rules.py`), 저장소 3종(`store.py`), 상태 변경(`service.py`), 상태→응답(`views.py`), 예외(`errors.py`)를 둔다. 요청·응답 스키마는 `app/schemas/inventory.py`, 라우터는 `app/api/inventory.py`(얇게)다. 재고 묶음 하나 = JSON 문서 하나(세션 저장과 같은 방식)이고, 바꾸는 요청은 owner별 잠금 안에서 복사본을 고친 뒤 성공했을 때만 저장한다(원자성).

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2(`Decimal` 수량), SQLite(`sqlite3`), Postgres(`psycopg_pool`), pytest.

**설계 문서:** `docs/superpowers/specs/2026-11-08-inventory-design.md` (이 PR은 1·2장, 5장의 품목·거래처·설정·기준·하루 마감·조회 경로, 저장소, 7장의 해당 테스트, 8장 #40)

## Global Constraints

- 모든 명령은 저장소 루트(`D:\ax_platform_5\ax_platform_5`)에서. 백엔드 테스트: `uv run --directory backend pytest`.
- 언제나 TDD: 실패하는 테스트 → 구현 → 통과.
- 오류 본문은 `{"detail": "<한국어 문장>"}`. 문구는 `backend/app/core/messages.py`에만 둔다.
- 응답에 실리는 모델은 `ContractModel`(`app/core/contract.py`)을 상속한다(`tests/test_contract.py`가 확인).
- 수량은 그 품목 단위의 `Decimal`, 소수 둘째 자리까지, 음수 불가(조정 값만 음수 허용). JSON 응답에서 `Decimal`은 문자열(예: `"7.5"`)이다. 테스트는 `Decimal(...)`로 바꿔 비교한다.
- 하루 마감에서 적지 않은 품목은 미입력이다(0이 아니다).
- 원장 기록이 있는 품목은 단위를 바꿀 수 없다(422).
- 목표 재고 < 최소 재고는 422.
- 없는 품목·거래처(경로의 id)는 404, 요청 본문 안의 잘못된 참조·규칙 위반은 422. 남의 재고는 보이지 않는다(owner가 곧 묶음 키).
- 커밋 메시지에 AI 공동저자·생성 표기를 넣지 않는다. 브랜치는 `task/40-inventory-core`(이미 있음).
- 판단은 순수 함수, 상태 변경은 `service.py` 한 곳. 라우터는 얇게.

## File Structure

| 파일 | 할 일 |
|---|---|
| Create `backend/app/inventory/__init__.py` | 빈 패키지 |
| Create `backend/app/inventory/models.py` | 저장 모델(`InventoryState`, `Item`, `Supplier`, `ReorderPolicy`, `InventorySettings`, 원장 항목, `Close`), 수량 타입, id 생성 |
| Create `backend/app/inventory/rules.py` | 순수 계산: 보유 수량, 마지막 실사 시각, 상태, 제안 주문량, 이상 수량 |
| Create `backend/app/inventory/store.py` | `InventoryStore` 계약과 메모리·SQLite·Postgres 구현 |
| Create `backend/app/inventory/errors.py` | `InventoryError`(422), `InventoryNotFound`(404) |
| Create `backend/app/inventory/service.py` | 상태 변경(품목·거래처·설정·기준·마감) |
| Create `backend/app/inventory/views.py` | 상태 → `InventoryView`(순수) |
| Create `backend/app/schemas/inventory.py` | 요청·응답 스키마 |
| Create `backend/app/api/inventory.py` | 라우터 `/api/v1/inventory` |
| Modify `backend/app/core/messages.py` | 재고 문구 |
| Modify `backend/app/core/postgres.py` | `_SCHEMA`에 `inventories` 표 |
| Modify `backend/app/core/storage.py` | `Storage.inventories` |
| Modify `backend/app/main.py` | `create_app(inventories=...)`, 잠금, 라우터 |
| Modify `backend/app/api/deps.py` | `Inventories`, `InventoryLocks` |
| Modify `backend/app/api/errors.py` | 재고 예외 처리기 |
| Modify `backend/app/api/responses.py` | 404 설명 |
| Modify `backend/tests/conftest.py` | Postgres TRUNCATE에 `inventories` |
| Create tests | `test_inventory_models.py`, `test_inventory_rules.py`, `test_inventory_store_contract.py`, `test_inventory_service.py`, `test_api_inventory.py` |
| Modify docs | `CLAUDE.md`(구조·실행), `docs/HANDOFF.md`, `docs/WBS.xlsx`, `frontend/openapi.json`·`frontend/src/api/schema.d.ts`(생성물) |

---

### Task 1: 저장 모델

**Files:**
- Create: `backend/app/inventory/__init__.py`, `backend/app/inventory/models.py`
- Test: `backend/tests/test_inventory_models.py`

**Interfaces:**
- Produces: `Quantity`, `PositiveQuantity`, `SignedQuantity`, `Money`(Annotated `Decimal`), `new_id(prefix) -> str`, `ItemKind`, `Procurement`, `MockOutcome`(StrEnum), `Item`, `Supplier`, `ReorderPolicy`, `InventorySettings`, `CountEntry`, `AdjustEntry`, `LedgerEntry`(판별 유니온, `type`), `Close`, `InventoryState`.

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_inventory_models.py`:

```python
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.inventory.models import (
    AdjustEntry,
    Close,
    CountEntry,
    InventoryState,
    Item,
    ItemKind,
    Procurement,
    ReorderPolicy,
)


def _item(**overrides) -> Item:
    values = {"name": "에코백", "kind": ItemKind.FINISHED, "unit": "개", "procurement": Procurement.MAKE}
    return Item(**(values | overrides))


def test_new_state_is_empty_with_default_settings():
    state = InventoryState(owner_id="client-aaaa")
    assert state.items == [] and state.ledger == [] and state.closes == []
    assert state.settings.anomaly_drop_ratio == Decimal("0.5")
    assert state.settings.stale_days == 7
    assert state.settings.address == ""


def test_ids_have_prefixes():
    assert _item().item_id.startswith("it_")
    assert CountEntry(item_id="it_x", quantity=Decimal(1)).entry_id.startswith("le_")
    assert Close(close_date=date(2026, 11, 8), counts={}).close_id.startswith("cl_")


def test_ledger_round_trips_through_json_with_its_type():
    state = InventoryState(owner_id="client-aaaa", items=[_item()])
    item_id = state.items[0].item_id
    state.ledger = [
        CountEntry(item_id=item_id, quantity=Decimal("10")),
        AdjustEntry(item_id=item_id, delta=Decimal("-2.5"), reason="파손"),
    ]

    loaded = InventoryState.model_validate_json(state.model_dump_json())

    assert [type(e) for e in loaded.ledger] == [CountEntry, AdjustEntry]
    assert loaded.ledger[1].delta == Decimal("-2.5")


@pytest.mark.parametrize("quantity", ["-1", "1.234"])
def test_count_quantity_is_non_negative_with_two_decimals(quantity):
    with pytest.raises(ValidationError):
        CountEntry(item_id="it_x", quantity=Decimal(quantity))


def test_policy_purchase_unit_must_be_positive():
    with pytest.raises(ValidationError):
        ReorderPolicy(min_stock=1, target_stock=2, purchase_unit=0, lead_days=3, unit_price=1000)
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_inventory_models.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.inventory'`)

- [ ] **Step 3: 구현**

`backend/app/inventory/__init__.py`: 빈 파일.

`backend/app/inventory/models.py`:

```python
"""재고 묶음(owner마다 하나)의 저장 모델. 수량은 저장하지 않고 원장에서 계산한다(rules.py).

원장(ledger)은 추가만 하고 고치지 않는다. 같은 품목의 순서는 목록 순서다(시각이 같아도 흔들리지 않는다).
새 필드는 기본값을 둬서 저장된 옛 문서도 그대로 읽히게 한다.
"""
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import Field

from app.core.contract import ContractModel
from app.core.results import utcnow

Quantity = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveQuantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
SignedQuantity = Annotated[Decimal, Field(max_digits=12, decimal_places=2)]
Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


class ItemKind(StrEnum):
    FINISHED = "finished"  # 완제품
    MATERIAL = "material"  # 재료
    PACKAGING = "packaging"  # 포장재


class Procurement(StrEnum):
    PURCHASE = "purchase"  # 거래처에서 산다
    MAKE = "make"  # 직접 만든다(부족하면 주문 대신 제작 알림)


class MockOutcome(StrEnum):
    """모의 거래처가 낼 결과(PR #41의 SupplierProvider Mock이 쓴다)."""

    ACCEPT = "accept"
    PRICE_CHANGED = "price_changed"
    OUT_OF_STOCK = "out_of_stock"
    UNKNOWN_THEN_ACCEPT = "unknown_then_accept"


class Item(ContractModel):
    item_id: str = Field(default_factory=lambda: new_id("it"))
    name: str
    option: str | None = None
    kind: ItemKind
    unit: str
    procurement: Procurement
    supplier_id: str | None = None  # 구매 품목만. 제작 품목은 늘 None
    archived: bool = False  # 지우지 않고 숨긴다(원장·주문 보존)


class Supplier(ContractModel):
    supplier_id: str = Field(default_factory=lambda: new_id("sup"))
    name: str
    kind: Literal["mock"] = "mock"
    mock_outcome: MockOutcome = MockOutcome.ACCEPT


class ReorderPolicy(ContractModel):
    min_stock: Quantity
    target_stock: Quantity
    purchase_unit: PositiveQuantity
    lead_days: int = Field(ge=0, le=365)
    unit_price: Money


class InventorySettings(ContractModel):
    address: str = Field(default="", max_length=200)
    anomaly_drop_ratio: Decimal = Field(default=Decimal("0.5"), gt=0, le=1, decimal_places=2)
    stale_days: int = Field(default=7, ge=1, le=90)


class CountEntry(ContractModel):
    """실사: 이 시점의 실제 수량(하루 마감, 일괄 등록의 현재 수량)."""

    type: Literal["count"] = "count"
    entry_id: str = Field(default_factory=lambda: new_id("le"))
    item_id: str
    quantity: Quantity
    at: datetime = Field(default_factory=utcnow)
    close_id: str | None = None


class AdjustEntry(ContractModel):
    """조정: 마지막 실사에 더하거나 뺀다. 사유가 필수다."""

    type: Literal["adjust"] = "adjust"
    entry_id: str = Field(default_factory=lambda: new_id("le"))
    item_id: str
    delta: SignedQuantity
    reason: str
    at: datetime = Field(default_factory=utcnow)
    close_id: str | None = None


LedgerEntry = Annotated[CountEntry | AdjustEntry, Field(discriminator="type")]


class Close(ContractModel):
    close_id: str = Field(default_factory=lambda: new_id("cl"))
    close_date: date
    counts: dict[str, Quantity]  # 적지 않은 품목은 미입력(0이 아니다)
    at: datetime = Field(default_factory=utcnow)


class InventoryState(ContractModel):
    owner_id: str
    items: list[Item] = Field(default_factory=list)
    suppliers: list[Supplier] = Field(default_factory=list)
    policies: dict[str, ReorderPolicy] = Field(default_factory=dict)  # 품목 id → 기준
    ledger: list[LedgerEntry] = Field(default_factory=list)
    closes: list[Close] = Field(default_factory=list)
    settings: InventorySettings = Field(default_factory=InventorySettings)
    updated_at: datetime = Field(default_factory=utcnow)
```

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_inventory_models.py -q`
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/inventory backend/tests/test_inventory_models.py
git commit -m "재고 저장 모델: 품목·거래처·기준·원장·마감"
```

---

### Task 2: 계산 규칙(순수 함수)

**Files:**
- Create: `backend/app/inventory/rules.py`
- Test: `backend/tests/test_inventory_rules.py`

**Interfaces:**
- Consumes: Task 1의 `CountEntry`, `AdjustEntry`, `LedgerEntry`, `ReorderPolicy`.
- Produces:
  - `on_hand(ledger: Sequence[LedgerEntry], item_id: str) -> Decimal | None`
  - `last_counted_at(ledger, item_id) -> datetime | None`
  - `StockStatus`(StrEnum: `uncounted`, `short`, `in_transit`, `ok`)
  - `item_status(on_hand_qty: Decimal | None, in_transit: Decimal, policy: ReorderPolicy | None) -> StockStatus`
  - `suggested_quantity(on_hand_qty, in_transit, policy) -> Decimal | None`
  - `AnomalyKind`(StrEnum: `increase`, `drop`), `Anomaly`(ContractModel: `item_id`, `previous`, `counted`, `kind`)
  - `find_anomalies(ledger, counts: Mapping[str, Decimal], drop_ratio: Decimal) -> list[Anomaly]`

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_inventory_rules.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal as D

import pytest

from app.inventory.models import AdjustEntry, CountEntry, ReorderPolicy
from app.inventory.rules import (
    Anomaly,
    AnomalyKind,
    StockStatus,
    find_anomalies,
    item_status,
    last_counted_at,
    on_hand,
    suggested_quantity,
)

T1 = datetime(2026, 11, 1, tzinfo=timezone.utc)
T2 = datetime(2026, 11, 2, tzinfo=timezone.utc)


def count(qty, item="a", at=T1):
    return CountEntry(item_id=item, quantity=D(qty), at=at)


def adjust(delta, item="a"):
    return AdjustEntry(item_id=item, delta=D(delta), reason="사유")


def policy(min_stock="10", target="30", unit="12"):
    return ReorderPolicy(min_stock=D(min_stock), target_stock=D(target), purchase_unit=D(unit), lead_days=3, unit_price=D(1000))


@pytest.mark.parametrize(
    ("ledger", "expected"),
    [
        ([], None),  # 센 적 없음 = 미입력
        ([adjust("3")], None),  # 실사 전 조정은 반영하지 않는다
        ([count("10")], D("10")),
        ([count("10"), adjust("-2.5")], D("7.5")),
        ([count("10"), adjust("-2"), count("4")], D("4")),  # 마지막 실사가 기준
        ([count("10"), count("99", item="b")], D("10")),  # 다른 품목은 무시
    ],
)
def test_on_hand(ledger, expected):
    assert on_hand(ledger, "a") == expected


def test_last_counted_at():
    assert last_counted_at([], "a") is None
    assert last_counted_at([count("1", at=T1), adjust("1"), count("2", at=T2)], "a") == T2


@pytest.mark.parametrize(
    ("qty", "in_transit", "pol", "expected"),
    [
        (None, D(0), policy(), StockStatus.UNCOUNTED),
        (D(5), D(0), policy(), StockStatus.SHORT),
        (D(5), D(5), policy(), StockStatus.IN_TRANSIT),  # 5+5 = 최소 10이면 부족 아님
        (D(5), D(0), None, StockStatus.OK),  # 기준이 없으면 부족 판정 안 함
        (D(20), D(0), policy(), StockStatus.OK),
    ],
)
def test_item_status(qty, in_transit, pol, expected):
    assert item_status(qty, in_transit, pol) is expected


@pytest.mark.parametrize(
    ("qty", "in_transit", "pol", "expected"),
    [
        (D(5), D(0), policy(), D(36)),  # 목표 30 − 5 = 25 → 12 단위로 올림 = 36
        (D(6), D(0), policy(), D(24)),  # 24 → 그대로 24
        (D("4.5"), D(0), policy(unit="0.5"), D("25.5")),
        (D(20), D(0), policy(), None),  # 부족 아님
        (None, D(0), policy(), None),  # 미입력
        (D(5), D(0), None, None),  # 기준 없음
    ],
)
def test_suggested_quantity(qty, in_transit, pol, expected):
    assert suggested_quantity(qty, in_transit, pol) == expected


def test_find_anomalies_increase_and_drop_in_counts_order():
    ledger = [count("10"), count("10", item="b"), count("10", item="c"), count("0", item="d")]
    counts = {"b": D(4), "a": D(11), "c": D(5), "d": D(0), "new": D(3)}

    found = find_anomalies(ledger, counts, D("0.5"))

    assert found == [
        Anomaly(item_id="b", previous=D(10), counted=D(4), kind=AnomalyKind.DROP),  # 60% 감소 > 50%
        Anomaly(item_id="a", previous=D(10), counted=D(11), kind=AnomalyKind.INCREASE),
    ]  # c는 정확히 50%라 아님, d는 직전 0, new는 센 적 없음
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_inventory_rules.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.inventory.rules'`)

- [ ] **Step 3: 구현**

`backend/app/inventory/rules.py`:

```python
"""재고 계산. 모두 값을 받아 값을 돌려주는 순수 함수다. 상태를 바꾸지 않는다."""
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum

from app.core.contract import ContractModel
from app.inventory.models import AdjustEntry, CountEntry, LedgerEntry, ReorderPolicy


class StockStatus(StrEnum):
    UNCOUNTED = "uncounted"  # 미입력(센 적 없음)
    SHORT = "short"  # 보유 + 배송 중 < 최소
    IN_TRANSIT = "in_transit"
    OK = "ok"


class AnomalyKind(StrEnum):
    INCREASE = "increase"  # 입고 없이 늘었다
    DROP = "drop"  # 기준보다 많이 줄었다


class Anomaly(ContractModel):
    item_id: str
    previous: Decimal
    counted: Decimal
    kind: AnomalyKind


def on_hand(ledger: Sequence[LedgerEntry], item_id: str) -> Decimal | None:
    """마지막 실사 + 그 뒤의 조정. 실사가 없으면 None(미입력). 실사 전 조정은 반영하지 않는다."""
    total: Decimal | None = None
    for entry in ledger:
        if entry.item_id != item_id:
            continue
        if isinstance(entry, CountEntry):
            total = entry.quantity
        elif isinstance(entry, AdjustEntry) and total is not None:
            total += entry.delta
    return total


def last_counted_at(ledger: Sequence[LedgerEntry], item_id: str) -> datetime | None:
    counted = [e.at for e in ledger if isinstance(e, CountEntry) and e.item_id == item_id]
    return counted[-1] if counted else None


def item_status(on_hand_qty: Decimal | None, in_transit: Decimal, policy: ReorderPolicy | None) -> StockStatus:
    if on_hand_qty is None:
        return StockStatus.UNCOUNTED
    if policy is not None and on_hand_qty + in_transit < policy.min_stock:
        return StockStatus.SHORT
    if in_transit > 0:
        return StockStatus.IN_TRANSIT
    return StockStatus.OK


def suggested_quantity(on_hand_qty: Decimal | None, in_transit: Decimal, policy: ReorderPolicy | None) -> Decimal | None:
    """부족할 때만 (목표 − 보유 − 배송 중)을 구매 단위로 올린 값. 아니면 None."""
    if policy is None or item_status(on_hand_qty, in_transit, policy) is not StockStatus.SHORT:
        return None
    gap = policy.target_stock - on_hand_qty - in_transit
    if gap <= 0:
        return None
    units = (gap / policy.purchase_unit).to_integral_value(rounding=ROUND_CEILING)
    return units * policy.purchase_unit


def find_anomalies(ledger: Sequence[LedgerEntry], counts: Mapping[str, Decimal], drop_ratio: Decimal) -> list[Anomaly]:
    """센 수량이 직전 보유보다 늘었거나, 직전 대비 drop_ratio보다 많이 줄었으면 확인이 필요하다(counts 순서)."""
    found: list[Anomaly] = []
    for item_id, counted in counts.items():
        previous = on_hand(ledger, item_id)
        if previous is None:
            continue
        if counted > previous:
            found.append(Anomaly(item_id=item_id, previous=previous, counted=counted, kind=AnomalyKind.INCREASE))
        elif previous > 0 and (previous - counted) / previous > drop_ratio:
            found.append(Anomaly(item_id=item_id, previous=previous, counted=counted, kind=AnomalyKind.DROP))
    return found
```

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_inventory_rules.py -q`
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/inventory/rules.py backend/tests/test_inventory_rules.py
git commit -m "재고 계산 규칙: 보유·상태·제안량·이상 수량"
```

---

### Task 3: 저장소 3종과 계약

**Files:**
- Create: `backend/app/inventory/store.py`
- Modify: `backend/app/core/postgres.py`(`_SCHEMA`), `backend/tests/conftest.py`(`postgres_pool`의 TRUNCATE)
- Test: `backend/tests/test_inventory_store_contract.py`

**Interfaces:**
- Consumes: `InventoryState`.
- Produces: `InventoryStore`(Protocol: `get(owner_id: str) -> InventoryState | None`, `save(state: InventoryState) -> None`), `InMemoryInventoryStore()`, `SqliteInventoryStore(path: Path)`, `PostgresInventoryStore(pool: ConnectionPool)`.

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_inventory_store_contract.py`:

```python
"""InventoryStore 계약. 새 저장소는 store 픽스처에 넣고 이 테스트를 그대로 통과해야 한다."""
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.inventory.models import CountEntry, InventoryState, Item, ItemKind, Procurement
from app.inventory.store import InMemoryInventoryStore, PostgresInventoryStore, SqliteInventoryStore


@pytest.fixture(params=["memory", "sqlite", "postgres"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemoryInventoryStore()
    if request.param == "sqlite":
        return SqliteInventoryStore(tmp_path / "sessions.db")
    return PostgresInventoryStore(request.getfixturevalue("postgres_pool"))


def _item() -> Item:
    return Item(name="에코백", kind=ItemKind.FINISHED, unit="개", procurement=Procurement.MAKE)


def test_missing_owner_returns_none(store):
    assert store.get("client-none") is None


def test_save_and_get_round_trip(store):
    state = InventoryState(owner_id="client-aaaa", items=[_item()])
    state.ledger.append(CountEntry(item_id=state.items[0].item_id, quantity=Decimal("2.5")))
    store.save(state)

    loaded = store.get("client-aaaa")

    assert loaded.items == state.items
    assert loaded.ledger[0].quantity == Decimal("2.5")


def test_get_returns_independent_copy(store):
    store.save(InventoryState(owner_id="client-aaaa"))
    loaded = store.get("client-aaaa")
    loaded.items.append(_item())
    assert store.get("client-aaaa").items == []


def test_save_stores_a_copy(store):
    state = InventoryState(owner_id="client-aaaa")
    store.save(state)
    state.items.append(_item())
    assert store.get("client-aaaa").items == []


def test_save_overwrites_and_bumps_updated_at(store):
    long_ago = datetime(2020, 1, 1, tzinfo=timezone.utc)
    state = InventoryState(owner_id="client-aaaa", updated_at=long_ago)
    store.save(state)
    state.items.append(_item())
    store.save(state)

    loaded = store.get("client-aaaa")
    assert len(loaded.items) == 1
    assert loaded.updated_at > long_ago


def test_owners_are_separate(store):
    store.save(InventoryState(owner_id="client-aaaa", items=[_item()]))
    store.save(InventoryState(owner_id="client-bbbb"))
    assert len(store.get("client-aaaa").items) == 1
    assert store.get("client-bbbb").items == []
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_inventory_store_contract.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.inventory.store'`)

- [ ] **Step 3: 구현**

`backend/app/inventory/store.py`:

```python
"""재고 저장소. owner마다 문서 하나(InventoryState JSON)다. 세션 저장소(app/core/store.py)와 같은 방식이다.

계약은 tests/test_inventory_store_contract.py가 세 구현 모두에 대해 확인한다.
- get은 복사본을 돌려준다. 없으면 None.
- save는 복사본을 저장하고 updated_at을 지금으로 바꾼다.
같은 묶음의 읽기 → 저장은 owner별 잠금(app.state.inventory_locks)이 하나로 묶는다(프로세스 하나 전제).
"""
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from app.core.results import utcnow
from app.inventory.models import InventoryState

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool


class InventoryStore(Protocol):
    def get(self, owner_id: str) -> InventoryState | None: ...

    def save(self, state: InventoryState) -> None: ...


class InMemoryInventoryStore:
    def __init__(self) -> None:
        self._states: dict[str, InventoryState] = {}

    def get(self, owner_id: str) -> InventoryState | None:
        state = self._states.get(owner_id)
        return state.model_copy(deep=True) if state else None

    def save(self, state: InventoryState) -> None:
        state.updated_at = utcnow()
        self._states[state.owner_id] = state.model_copy(deep=True)


_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS inventories (
    owner_id TEXT PRIMARY KEY,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


class SqliteInventoryStore:
    """세션과 같은 SQLite 파일(DATABASE_PATH)의 inventories 표. 요청마다 연결을 열고 닫는다."""

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as conn:
            conn.executescript(_SQLITE_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        with closing(sqlite3.connect(self._path)) as conn:
            with conn:
                yield conn

    def get(self, owner_id: str) -> InventoryState | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM inventories WHERE owner_id = ?", (owner_id,)).fetchone()
        return InventoryState.model_validate_json(row[0]) if row else None

    def save(self, state: InventoryState) -> None:
        state.updated_at = utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO inventories (owner_id, updated_at, data) VALUES (?, ?, ?) "
                "ON CONFLICT(owner_id) DO UPDATE SET updated_at = excluded.updated_at, data = excluded.data",
                (state.owner_id, state.updated_at.isoformat(), state.model_dump_json()),
            )


class PostgresInventoryStore:
    """inventories 표는 app/core/postgres.py의 _SCHEMA가 풀을 열 때 만든다."""

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def get(self, owner_id: str) -> InventoryState | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT data::text FROM inventories WHERE owner_id = %s", (owner_id,)).fetchone()
        return InventoryState.model_validate_json(row[0]) if row else None

    def save(self, state: InventoryState) -> None:
        from app.core.postgres import without_nul

        state.updated_at = utcnow()
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO inventories (owner_id, updated_at, data) VALUES (%s, %s, %s::jsonb) "
                "ON CONFLICT (owner_id) DO UPDATE SET updated_at = EXCLUDED.updated_at, data = EXCLUDED.data",
                (state.owner_id, state.updated_at, without_nul(state.model_dump_json())),
            )
```

`backend/app/core/postgres.py`의 `_SCHEMA` 끝(`assets` 표 다음, 닫는 `"""` 앞)에 더한다:

```sql
CREATE TABLE IF NOT EXISTS inventories (
    owner_id TEXT PRIMARY KEY,
    updated_at TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL
);
```

`backend/tests/conftest.py`의 `postgres_pool` 픽스처:

```python
        conn.execute("TRUNCATE sessions, assets, inventories")
```

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_inventory_store_contract.py tests/test_store_contract.py -q`
Expected: 모두 PASS(Postgres를 띄울 수 없는 환경이면 postgres 매개변수만 skip)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/inventory/store.py backend/app/core/postgres.py backend/tests/conftest.py backend/tests/test_inventory_store_contract.py
git commit -m "재고 저장소: 메모리·SQLite·Postgres와 계약 테스트"
```

---

### Task 4: 예외·문구·앱 연결

**Files:**
- Create: `backend/app/inventory/errors.py`
- Modify: `backend/app/core/messages.py`, `backend/app/core/storage.py`, `backend/app/main.py`, `backend/app/api/deps.py`, `backend/app/api/errors.py`, `backend/app/api/responses.py`
- Test: `backend/tests/test_api_inventory.py`(이 Task에서 파일을 만들고 뒤 Task가 더한다)

**Interfaces:**
- Produces:
  - `InventoryError(message: str)`(→ 422), `InventoryNotFound(message: str)`(→ 404)
  - `Storage.inventories: InventoryStore`(필드 순서: `sessions, assets, inventories, open, close`)
  - `create_app(..., inventories: InventoryStore | None = None)`, `app.state.inventories`, `app.state.inventory_locks`(`SessionLocks`, 키는 owner)
  - `deps.Inventories`, `deps.InventoryLocks`
  - 문구 상수(아래)

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_api_inventory.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_api_inventory.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.inventory.errors'`)

- [ ] **Step 3: 구현**

`backend/app/inventory/errors.py`:

```python
"""재고 예외. 메시지는 사용자에게 보이는 한국어 문장(app/core/messages.py)이다. 처리기는 app/api/errors.py."""


class InventoryError(Exception):
    """요청이 재고 규칙에 맞지 않음(422). 상태는 저장하지 않는다."""


class InventoryNotFound(Exception):
    """경로의 품목·거래처가 없음(404)."""
```

`backend/app/core/messages.py` 끝에 더한다:

```python
INVENTORY_ITEM_NOT_FOUND_MESSAGE = "그 품목을 찾을 수 없습니다."
INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE = "그 거래처를 찾을 수 없습니다."
INVENTORY_UNKNOWN_SUPPLIER_MESSAGE = "없는 거래처를 골랐습니다."
INVENTORY_UNKNOWN_ITEM_MESSAGE = "없거나 숨긴 품목이 들어 있습니다."
INVENTORY_UNIT_LOCKED_MESSAGE = "수량 기록이 있는 품목은 단위를 바꿀 수 없습니다. 새 품목으로 등록해 주세요."
INVENTORY_TARGET_BELOW_MIN_MESSAGE = "목표 재고는 최소 재고보다 작을 수 없습니다."
INVENTORY_EMPTY_CLOSE_MESSAGE = "마감할 수량이나 조정을 하나 이상 입력해 주세요."
INVENTORY_ADJUST_UNCOUNTED_MESSAGE = "수량을 센 적 없는 품목은 조정할 수 없습니다. 먼저 수량을 입력해 주세요."
INVENTORY_NEGATIVE_STOCK_MESSAGE = "조정하면 수량이 0보다 작아집니다."


def duplicate_item_message(name: str) -> str:
    return f"같은 품목이 이미 있습니다: {name}"


def unconfirmed_anomaly_message(names: Iterable[str]) -> str:
    return f"확인이 필요한 수량이 있습니다: {', '.join(names)}"
```

`backend/app/core/storage.py`:

```python
from app.inventory.store import InMemoryInventoryStore, InventoryStore, SqliteInventoryStore
```

`Storage` 필드를 `sessions`, `assets`, `inventories: InventoryStore`, `open`, `close` 순서로 바꾸고 `build_storage`의 세 반환을 고친다:

```python
    if kind == "postgres":
        ...
        from app.inventory.store import PostgresInventoryStore

        pool = make_pool(database_url)
        return Storage(
            PostgresSessionStore(pool), PostgresAssetStore(pool), PostgresInventoryStore(pool),
            lambda: open_pool(pool), pool.close,
        )
    if kind == "sqlite":
        return Storage(
            SqliteSessionStore(database_path), LocalAssetStore(asset_dir), SqliteInventoryStore(database_path),
            _nothing, _nothing,
        )
    return Storage(InMemorySessionStore(), InMemoryAssetStore(), InMemoryInventoryStore(), _nothing, _nothing)
```

`build_storage` docstring에 "재고 저장소도 같은 저장 방식으로 만든다."를 더한다. `Storage(`를 만드는 다른 곳이 없는지 `rg "Storage\(" backend/app backend/tests backend/scripts ../scripts`로 확인하고 있으면 같이 고친다.

`backend/app/main.py`:

```python
from app.api import assets as assets_api, coaching, inventory as inventory_api
from app.inventory.store import InventoryStore
```

`create_app` 매개변수 끝에 `inventories: InventoryStore | None = None`을 더하고:

```python
    storage = None
    if store is None or assets is None or inventories is None:  # 연결은 만들 때가 아니라 서버가 시작할 때(lifespan) 한다
        storage = build_storage(...)  # 그대로
    ...
    app.state.inventories = inventories or storage.inventories
    app.state.inventory_locks = SessionLocks()  # 키는 owner(재고 묶음 하나)
    ...
    app.include_router(inventory_api.router)
```

이 Task에서는 `backend/app/api/inventory.py`를 라우터만 있는 최소 파일로 만든다(Task 7이 경로를 채운다):

```python
"""재고 API. 상태 변경은 app/inventory/service.py, 응답은 app/inventory/views.py가 한다."""
from fastapi import APIRouter

from app.api.responses import error_responses

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], responses=error_responses(500))
```

`backend/app/api/deps.py`:

```python
from app.inventory.store import InventoryStore


def get_inventories(request: Request) -> InventoryStore:
    return request.app.state.inventories


def get_inventory_locks(request: Request) -> SessionLocks:
    return request.app.state.inventory_locks


Inventories = Annotated[InventoryStore, Depends(get_inventories)]
InventoryLocks = Annotated[SessionLocks, Depends(get_inventory_locks)]
```

`backend/app/api/errors.py`의 `install_error_handlers` 안(`HarnessError` 처리기 다음)에 더한다:

```python
    @app.exception_handler(InventoryError)
    async def inventory_error(request: Request, exc: InventoryError) -> JSONResponse:
        return _error(422, str(exc))

    @app.exception_handler(InventoryNotFound)
    async def inventory_not_found(request: Request, exc: InventoryNotFound) -> JSONResponse:
        return _error(404, str(exc))
```

(import: `from app.inventory.errors import InventoryError, InventoryNotFound`)

`backend/app/api/responses.py`의 `_DESCRIPTIONS`:

```python
    404: "찾는 대상(과제·세션·결과·파일·품목·거래처)이 없음",
    422: "요청 형식(사용자 식별 헤더 포함)이나 답변·재고 규칙에 맞지 않음",
```

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_api_inventory.py tests/test_api_errors.py tests/test_store_contract.py -q`
Expected: 모두 PASS. 이어서 전체 `uv run --directory backend pytest -q`도 PASS(기존 테스트가 404·422 설명 문구를 단정하면 그 기대값을 새 문구로 고친다).

- [ ] **Step 5: 커밋**

```bash
git add backend/app backend/tests/test_api_inventory.py
git commit -m "재고 저장소·잠금·예외 처리기를 앱에 연결"
```

---

### Task 5: 요청 스키마와 품목·거래처·설정·기준 변경(service)

**Files:**
- Create: `backend/app/schemas/inventory.py`(요청 스키마. 응답 스키마는 Task 7이 더한다), `backend/app/inventory/service.py`
- Test: `backend/tests/test_inventory_service.py`

**Interfaces:**
- Consumes: Task 1 모델, Task 2 `on_hand`, Task 4 예외·문구.
- Produces(요청 스키마): `ItemDraft`, `BulkItemsRequest`(`items: list[ItemDraft]` 1~200), `ItemPatch`, `SupplierDraft`, `SupplierPatch`.
- Produces(service):
  - `add_items(state: InventoryState, drafts: Sequence[ItemDraft]) -> list[Item]`
  - `update_item(state, item_id: str, patch: ItemPatch) -> Item`
  - `add_supplier(state, draft: SupplierDraft) -> Supplier`
  - `update_supplier(state, supplier_id: str, patch: SupplierPatch) -> Supplier`
  - `set_settings(state, settings: InventorySettings) -> None`
  - `set_policy(state, item_id: str, policy: ReorderPolicy) -> None`
  - `find_item(state, item_id) -> Item`(없으면 `InventoryNotFound`)

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_inventory_service.py`:

```python
from decimal import Decimal as D

import pytest

from app.core.messages import (
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    duplicate_item_message,
)
from app.inventory import service
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import CountEntry, InventorySettings, InventoryState, ItemKind, MockOutcome, Procurement, ReorderPolicy
from app.inventory.rules import on_hand
from app.schemas.inventory import ItemDraft, ItemPatch, SupplierDraft, SupplierPatch


def draft(name="에코백", **overrides) -> ItemDraft:
    values = {"name": name, "kind": "finished", "unit": "개", "procurement": "make"}
    return ItemDraft(**(values | overrides))


def fresh() -> InventoryState:
    return InventoryState(owner_id="client-aaaa")


def test_add_items_records_initial_quantity_as_count():
    state = fresh()
    items = service.add_items(state, [draft(quantity=D(5)), draft("원단", kind="material", unit="m")])

    assert [i.name for i in state.items] == ["에코백", "원단"]
    assert on_hand(state.ledger, items[0].item_id) == D(5)
    assert on_hand(state.ledger, items[1].item_id) is None  # 수량을 안 적으면 미입력
    assert isinstance(state.ledger[0], CountEntry)


def test_add_items_strips_names():
    state = fresh()
    service.add_items(state, [draft("  에코백  ", option=" 검정 ")])
    assert (state.items[0].name, state.items[0].option) == ("에코백", "검정")


def test_add_items_rejects_duplicates_in_batch_and_existing():
    state = fresh()
    service.add_items(state, [draft(option="검정")])
    with pytest.raises(InventoryError, match=duplicate_item_message("에코백")):
        service.add_items(state, [draft(option="검정")])
    with pytest.raises(InventoryError):
        service.add_items(state, [draft("원단"), draft("원단")])
    service.add_items(state, [draft(option="흰색")])  # 옵션이 다르면 다른 품목
    assert len(state.items) == 2


def test_add_items_checks_supplier_and_drops_it_for_make():
    state = fresh()
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_SUPPLIER_MESSAGE):
        service.add_items(state, [draft(procurement="purchase", supplier_id="sup_none")])
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회"))
    items = service.add_items(
        state,
        [draft("원단", procurement="purchase", supplier_id=supplier.supplier_id), draft("에코백", supplier_id=supplier.supplier_id)],
    )
    assert items[0].supplier_id == supplier.supplier_id
    assert items[1].supplier_id is None  # 제작 품목에는 거래처가 없다


def test_update_item_patches_only_given_fields_and_clears_option():
    state = fresh()
    [item] = service.add_items(state, [draft(option="검정")])

    service.update_item(state, item.item_id, ItemPatch(name="큰 에코백"))
    assert (state.items[0].name, state.items[0].option) == ("큰 에코백", "검정")

    service.update_item(state, item.item_id, ItemPatch(option=None))
    assert state.items[0].option is None

    service.update_item(state, item.item_id, ItemPatch(archived=True))
    assert state.items[0].archived is True


def test_update_item_locks_unit_once_ledger_has_entries():
    state = fresh()
    [counted, empty] = service.add_items(state, [draft(quantity=D(1)), draft("원단", unit="m")])

    with pytest.raises(InventoryError, match=INVENTORY_UNIT_LOCKED_MESSAGE):
        service.update_item(state, counted.item_id, ItemPatch(unit="묶음"))
    service.update_item(state, counted.item_id, ItemPatch(unit="개"))  # 같은 단위는 괜찮다
    service.update_item(state, empty.item_id, ItemPatch(unit="cm"))
    assert state.items[1].unit == "cm"


def test_update_item_unknown_id_is_not_found():
    with pytest.raises(InventoryNotFound, match=INVENTORY_ITEM_NOT_FOUND_MESSAGE):
        service.update_item(fresh(), "it_none", ItemPatch(name="x"))


def test_update_item_rejects_becoming_a_duplicate():
    state = fresh()
    [_, other] = service.add_items(state, [draft(), draft("원단")])
    with pytest.raises(InventoryError):
        service.update_item(state, other.item_id, ItemPatch(name="에코백"))


def test_suppliers_add_and_update():
    state = fresh()
    supplier = service.add_supplier(state, SupplierDraft(name="원단상회"))
    service.update_supplier(state, supplier.supplier_id, SupplierPatch(mock_outcome=MockOutcome.OUT_OF_STOCK))
    assert state.suppliers[0].mock_outcome is MockOutcome.OUT_OF_STOCK
    assert state.suppliers[0].name == "원단상회"
    with pytest.raises(InventoryNotFound, match=INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE):
        service.update_supplier(state, "sup_none", SupplierPatch(name="x"))


def test_set_policy_requires_target_at_least_min():
    state = fresh()
    [item] = service.add_items(state, [draft()])
    ok = ReorderPolicy(min_stock=D(5), target_stock=D(5), purchase_unit=D(1), lead_days=2, unit_price=D(0))
    service.set_policy(state, item.item_id, ok)
    assert state.policies[item.item_id] == ok

    bad = ok.model_copy(update={"target_stock": D(4)})
    with pytest.raises(InventoryError, match=INVENTORY_TARGET_BELOW_MIN_MESSAGE):
        service.set_policy(state, item.item_id, bad)
    with pytest.raises(InventoryNotFound):
        service.set_policy(state, "it_none", ok)


def test_set_settings_replaces_settings():
    state = fresh()
    service.set_settings(state, InventorySettings(address="서울시 어딘가", stale_days=3))
    assert state.settings.address == "서울시 어딘가"
    assert state.settings.stale_days == 3
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_inventory_service.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.schemas.inventory'`)

- [ ] **Step 3: 구현**

`backend/app/schemas/inventory.py`:

```python
"""재고 API 요청·응답 스키마. 저장 모델은 app/inventory/models.py에 있다."""
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.inventory.models import ItemKind, MockOutcome, Procurement, Quantity

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
OptionText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
Unit = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]


class ItemDraft(BaseModel):
    """품목 하나 등록(S01 일괄 등록의 한 줄, S02 개별 등록). quantity를 적으면 그 수량으로 실사를 남긴다."""

    name: Name
    option: OptionText | None = None
    kind: ItemKind
    unit: Unit
    procurement: Procurement = Procurement.PURCHASE
    supplier_id: str | None = None
    quantity: Quantity | None = None


class BulkItemsRequest(BaseModel):
    items: list[ItemDraft] = Field(min_length=1, max_length=200)


class ItemPatch(BaseModel):
    """보낸 필드만 바꾼다. name·kind·unit·procurement·archived는 null이면 그대로, option·supplier_id는 null이면 비운다."""

    name: Name | None = None
    option: OptionText | None = None
    kind: ItemKind | None = None
    unit: Unit | None = None
    procurement: Procurement | None = None
    supplier_id: str | None = None
    archived: bool | None = None


class SupplierDraft(BaseModel):
    name: Name
    mock_outcome: MockOutcome = MockOutcome.ACCEPT


class SupplierPatch(BaseModel):
    """보낸 필드만 바꾼다. null이면 그대로."""

    name: Name | None = None
    mock_outcome: MockOutcome | None = None
```

`backend/app/inventory/service.py`:

```python
"""재고 상태 변경은 이 모듈 한 곳에서 한다. 판단은 rules.py(순수)에 맡긴다.

함수는 받은 state를 고친다. 규칙에 어긋나면 InventoryError(422)·InventoryNotFound(404)를 던지고,
라우터는 그때 저장하지 않으므로(복사본을 고치고 성공해야 저장) 요청은 원자적이다.
"""
from collections.abc import Sequence

from app.core.messages import (
    INVENTORY_ITEM_NOT_FOUND_MESSAGE,
    INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE,
    INVENTORY_TARGET_BELOW_MIN_MESSAGE,
    INVENTORY_UNIT_LOCKED_MESSAGE,
    INVENTORY_UNKNOWN_SUPPLIER_MESSAGE,
    duplicate_item_message,
)
from app.inventory.errors import InventoryError, InventoryNotFound
from app.inventory.models import (
    CountEntry,
    InventorySettings,
    InventoryState,
    Item,
    Procurement,
    ReorderPolicy,
    Supplier,
)
from app.schemas.inventory import ItemDraft, ItemPatch, SupplierDraft, SupplierPatch

_KEEP_WHEN_NULL = ("name", "kind", "unit", "procurement", "archived")


def find_item(state: InventoryState, item_id: str) -> Item:
    for item in state.items:
        if item.item_id == item_id:
            return item
    raise InventoryNotFound(INVENTORY_ITEM_NOT_FOUND_MESSAGE)


def _find_supplier(state: InventoryState, supplier_id: str) -> Supplier:
    for supplier in state.suppliers:
        if supplier.supplier_id == supplier_id:
            return supplier
    raise InventoryNotFound(INVENTORY_SUPPLIER_NOT_FOUND_MESSAGE)


def _checked_supplier(state: InventoryState, procurement: Procurement, supplier_id: str | None) -> str | None:
    """제작 품목은 거래처가 없다. 구매 품목의 거래처는 있어야 한다(본문 안의 잘못된 참조라 422)."""
    if procurement is Procurement.MAKE or supplier_id is None:
        return None
    if not any(s.supplier_id == supplier_id for s in state.suppliers):
        raise InventoryError(INVENTORY_UNKNOWN_SUPPLIER_MESSAGE)
    return supplier_id


def _ensure_unique(items: Sequence[Item]) -> None:
    """숨기지 않은 품목끼리 이름·옵션이 겹치면 안 된다."""
    seen: set[tuple[str, str | None]] = set()
    for item in items:
        if item.archived:
            continue
        key = (item.name, item.option)
        if key in seen:
            raise InventoryError(duplicate_item_message(item.name))
        seen.add(key)


def add_items(state: InventoryState, drafts: Sequence[ItemDraft]) -> list[Item]:
    added = [
        Item(
            name=d.name,
            option=d.option,
            kind=d.kind,
            unit=d.unit,
            procurement=d.procurement,
            supplier_id=_checked_supplier(state, d.procurement, d.supplier_id),
        )
        for d in drafts
    ]
    _ensure_unique([*state.items, *added])
    state.items.extend(added)
    for item, d in zip(added, drafts):
        if d.quantity is not None:
            state.ledger.append(CountEntry(item_id=item.item_id, quantity=d.quantity))
    return added


def update_item(state: InventoryState, item_id: str, patch: ItemPatch) -> Item:
    item = find_item(state, item_id)
    changes = {
        name: getattr(patch, name)
        for name in patch.model_fields_set
        if not (name in _KEEP_WHEN_NULL and getattr(patch, name) is None)
    }
    if "unit" in changes and changes["unit"] != item.unit and any(e.item_id == item_id for e in state.ledger):
        raise InventoryError(INVENTORY_UNIT_LOCKED_MESSAGE)
    updated = item.model_copy(update=changes)
    updated.supplier_id = _checked_supplier(state, updated.procurement, updated.supplier_id)
    others = [i for i in state.items if i.item_id != item_id]
    _ensure_unique([*others, updated])
    state.items = [updated if i.item_id == item_id else i for i in state.items]
    return updated


def add_supplier(state: InventoryState, draft: SupplierDraft) -> Supplier:
    supplier = Supplier(name=draft.name, mock_outcome=draft.mock_outcome)
    state.suppliers.append(supplier)
    return supplier


def update_supplier(state: InventoryState, supplier_id: str, patch: SupplierPatch) -> Supplier:
    supplier = _find_supplier(state, supplier_id)
    changes = {name: getattr(patch, name) for name in patch.model_fields_set if getattr(patch, name) is not None}
    updated = supplier.model_copy(update=changes)
    state.suppliers = [updated if s.supplier_id == supplier_id else s for s in state.suppliers]
    return updated


def set_settings(state: InventoryState, settings: InventorySettings) -> None:
    state.settings = settings


def set_policy(state: InventoryState, item_id: str, policy: ReorderPolicy) -> None:
    find_item(state, item_id)
    if policy.target_stock < policy.min_stock:
        raise InventoryError(INVENTORY_TARGET_BELOW_MIN_MESSAGE)
    state.policies[item_id] = policy
```

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_inventory_service.py -q`
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/schemas/inventory.py backend/app/inventory/service.py backend/tests/test_inventory_service.py
git commit -m "재고 품목·거래처·설정·보충 기준 변경"
```

---

### Task 6: 하루 마감(service)

**Files:**
- Modify: `backend/app/schemas/inventory.py`(요청 `Adjustment`, `CloseCheckRequest`, `CloseRequest`), `backend/app/inventory/service.py`
- Test: `backend/tests/test_inventory_service.py`(더한다)

**Interfaces:**
- Consumes: Task 2 `find_anomalies`, `on_hand`, `Anomaly`.
- Produces:
  - `Adjustment(item_id: str, delta: SignedQuantity(≠0), reason: str 1~200)`
  - `CloseCheckRequest(counts: dict[str, Quantity])`
  - `CloseRequest(close_date: date, counts: dict[str, Quantity] = {}, adjustments: list[Adjustment] = [], confirmed: list[str] = [])`
  - `check_close(state, counts: Mapping[str, Decimal]) -> list[Anomaly]`(상태를 바꾸지 않는다)
  - `record_close(state, request: CloseRequest) -> Close`

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_inventory_service.py` 끝에 더한다:

```python
from datetime import date

from app.core.messages import (
    INVENTORY_ADJUST_UNCOUNTED_MESSAGE,
    INVENTORY_EMPTY_CLOSE_MESSAGE,
    INVENTORY_NEGATIVE_STOCK_MESSAGE,
    INVENTORY_UNKNOWN_ITEM_MESSAGE,
    unconfirmed_anomaly_message,
)
from app.inventory.models import AdjustEntry
from app.inventory.rules import AnomalyKind
from app.schemas.inventory import Adjustment, CloseRequest

DAY = date(2026, 11, 8)


def stocked(*quantities):
    state = fresh()
    items = service.add_items(state, [draft(f"품목{i}", quantity=q) for i, q in enumerate(quantities)])
    return state, [i.item_id for i in items]


def test_record_close_appends_counts_then_adjustments_and_close():
    state, [a, b] = stocked(D(10), D(10))
    close = service.record_close(
        state,
        CloseRequest(close_date=DAY, counts={a: D(8)}, adjustments=[Adjustment(item_id=a, delta=D(-1), reason="파손")]),
    )

    assert state.closes == [close]
    assert close.counts == {a: D(8)}  # b는 미입력(0이 아니다)
    assert on_hand(state.ledger, a) == D(7)
    assert on_hand(state.ledger, b) == D(10)
    assert [type(e) for e in state.ledger[-2:]] == [CountEntry, AdjustEntry]
    assert all(e.close_id == close.close_id for e in state.ledger[-2:])


def test_check_close_lists_anomalies_without_changing_state():
    state, [a, b] = stocked(D(10), D(10))
    before = state.model_copy(deep=True)

    found = service.check_close(state, {a: D(12), b: D(9)})

    assert [(x.item_id, x.kind) for x in found] == [(a, AnomalyKind.INCREASE)]
    assert state == before


def test_record_close_requires_confirming_every_anomaly():
    state, [a, b] = stocked(D(10), D(10))
    counts = {a: D(12), b: D(1)}
    with pytest.raises(InventoryError, match=unconfirmed_anomaly_message(["품목1"])):  # 품목0(a)은 확인했다
        service.record_close(state, CloseRequest(close_date=DAY, counts=counts, confirmed=[a]))
    assert state.closes == []  # 실패하면 아무것도 남기지 않는다(service는 검사를 모두 끝낸 뒤 고친다)

    service.record_close(state, CloseRequest(close_date=DAY, counts=counts, confirmed=[a, b]))
    assert on_hand(state.ledger, b) == D(1)


def test_same_day_close_again_last_count_wins():
    state, [a] = stocked(D(10))
    service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(9)}))
    service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(8)}))
    assert on_hand(state.ledger, a) == D(8)
    assert len(state.closes) == 2


@pytest.mark.parametrize(
    ("request_kwargs", "message"),
    [
        ({}, INVENTORY_EMPTY_CLOSE_MESSAGE),
        ({"counts": {"it_none": D(1)}}, INVENTORY_UNKNOWN_ITEM_MESSAGE),
        ({"adjustments": [{"item_id": "NEW", "delta": "1", "reason": "r"}]}, INVENTORY_ADJUST_UNCOUNTED_MESSAGE),
        ({"adjustments": [{"item_id": "A", "delta": "-11", "reason": "r"}]}, INVENTORY_NEGATIVE_STOCK_MESSAGE),
    ],
)
def test_record_close_rejections_leave_state_untouched(request_kwargs, message):
    state, [a] = stocked(D(10))
    [new] = service.add_items(state, [draft("새 품목")])
    for adj in request_kwargs.get("adjustments", []):
        adj["item_id"] = {"A": a, "NEW": new.item_id}[adj["item_id"]]
    before = state.model_copy(deep=True)

    with pytest.raises(InventoryError, match=message):
        service.record_close(state, CloseRequest(close_date=DAY, **request_kwargs))
    assert state == before


def test_archived_items_cannot_be_closed():
    state, [a] = stocked(D(10))
    service.update_item(state, a, ItemPatch(archived=True))
    with pytest.raises(InventoryError, match=INVENTORY_UNKNOWN_ITEM_MESSAGE):
        service.record_close(state, CloseRequest(close_date=DAY, counts={a: D(1)}))


def test_adjust_counted_in_same_close_is_allowed():
    state = fresh()
    [item] = service.add_items(state, [draft()])
    service.record_close(
        state,
        CloseRequest(
            close_date=DAY,
            counts={item.item_id: D(3)},
            adjustments=[Adjustment(item_id=item.item_id, delta=D(2), reason="찾음")],
        ),
    )
    assert on_hand(state.ledger, item.item_id) == D(5)


def test_adjustment_delta_cannot_be_zero():
    with pytest.raises(ValueError):
        Adjustment(item_id="it_x", delta=D(0), reason="r")
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_inventory_service.py -q`
Expected: FAIL (`ImportError: cannot import name 'Adjustment'`)

- [ ] **Step 3: 구현**

`backend/app/schemas/inventory.py`에 더한다(import에 `date`, `field_validator`, `SignedQuantity` 추가):

```python
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class Adjustment(BaseModel):
    """S05-check 조정: 마지막 실사에 더하거나 뺀다. 사유 필수, 0은 받지 않는다."""

    item_id: str
    delta: SignedQuantity
    reason: Reason

    @field_validator("delta")
    @classmethod
    def _not_zero(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("조정 값은 0일 수 없습니다.")
        return value


class CloseCheckRequest(BaseModel):
    counts: dict[str, Quantity] = Field(default_factory=dict)


class CloseRequest(BaseModel):
    """S05 하루 마감. counts에 없는 품목은 미입력. confirmed는 이상 수량을 확인한 품목 id."""

    close_date: date
    counts: dict[str, Quantity] = Field(default_factory=dict)
    adjustments: list[Adjustment] = Field(default_factory=list)
    confirmed: list[str] = Field(default_factory=list)
```

`backend/app/inventory/service.py`에 더한다(import: `Mapping`, `Decimal`, 새 문구, `AdjustEntry`, `Close`, `find_anomalies`, `on_hand`, `Anomaly`, `CloseRequest`):

```python
def _active_item_ids(state: InventoryState) -> set[str]:
    return {i.item_id for i in state.items if not i.archived}


def check_close(state: InventoryState, counts: Mapping[str, Decimal]) -> list[Anomaly]:
    """저장하지 않고 이상 수량만 찾는다."""
    return find_anomalies(state.ledger, counts, state.settings.anomaly_drop_ratio)


def record_close(state: InventoryState, request: CloseRequest) -> Close:
    """검사를 모두 끝낸 뒤에만 state를 고친다(실패하면 그대로)."""
    if not request.counts and not request.adjustments:
        raise InventoryError(INVENTORY_EMPTY_CLOSE_MESSAGE)
    active = _active_item_ids(state)
    touched = set(request.counts) | {a.item_id for a in request.adjustments}
    if not touched <= active:
        raise InventoryError(INVENTORY_UNKNOWN_ITEM_MESSAGE)

    unconfirmed = [a for a in check_close(state, request.counts) if a.item_id not in set(request.confirmed)]
    if unconfirmed:
        raise InventoryError(unconfirmed_anomaly_message(find_item(state, a.item_id).name for a in unconfirmed))

    close = Close(close_date=request.close_date, counts=dict(request.counts))
    entries = [CountEntry(item_id=i, quantity=q, close_id=close.close_id) for i, q in request.counts.items()]
    entries += [
        AdjustEntry(item_id=a.item_id, delta=a.delta, reason=a.reason, close_id=close.close_id)
        for a in request.adjustments
    ]
    ledger = [*state.ledger, *entries]
    for item_id in {a.item_id for a in request.adjustments}:
        result = on_hand(ledger, item_id)
        if result is None:
            raise InventoryError(INVENTORY_ADJUST_UNCOUNTED_MESSAGE)
        if result < 0:
            raise InventoryError(INVENTORY_NEGATIVE_STOCK_MESSAGE)

    state.ledger = ledger
    state.closes.append(close)
    return close
```

주의: 조정의 미입력 판정은 "`on_hand`가 None"으로 한다. `on_hand`는 실사 전 조정을 무시하므로, 실사 없이 조정만 있으면 None이 된다.

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_inventory_service.py -q`
Expected: 모두 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/app/schemas/inventory.py backend/app/inventory/service.py backend/tests/test_inventory_service.py
git commit -m "하루 마감: 실사·조정 기록과 이상 수량 확인"
```

---

### Task 7: 응답 뷰와 API 경로

**Files:**
- Create: `backend/app/inventory/views.py`
- Modify: `backend/app/schemas/inventory.py`(응답 모델), `backend/app/api/inventory.py`
- Test: `backend/tests/test_api_inventory.py`(더한다)

**Interfaces:**
- Consumes: Task 2 규칙, Task 4 연결, Task 5·6 service·요청 스키마.
- Produces:
  - 응답 `ItemView(item: Item, on_hand: Decimal | None, in_transit: Decimal, status: StockStatus, suggested_quantity: Decimal | None, policy: ReorderPolicy | None, last_counted_at: datetime | None)`
  - `InventoryView(items: list[ItemView], suppliers: list[Supplier], settings: InventorySettings, last_close: Close | None)`
  - `CloseCheckView(anomalies: list[Anomaly])`, `CloseView(close: Close, inventory: InventoryView)`
  - `to_inventory_view(state: InventoryState) -> InventoryView`(순수. `in_transit`은 주문이 아직 없어 0이다. PR #41이 주문으로 계산하게 바꾼다)
  - 경로(모두 `X-Client-Id` 필요):

| 메서드·경로 | 본문 | 응답 | 오류 |
|---|---|---|---|
| `GET /api/v1/inventory` | — | `InventoryView` | 422 |
| `POST …/items/bulk` | `BulkItemsRequest` | 201 `InventoryView` | 422 |
| `POST …/items` | `ItemDraft` | 201 `InventoryView` | 422 |
| `PATCH …/items/{item_id}` | `ItemPatch` | `InventoryView` | 404, 422 |
| `POST …/suppliers` | `SupplierDraft` | 201 `InventoryView` | 422 |
| `PATCH …/suppliers/{supplier_id}` | `SupplierPatch` | `InventoryView` | 404, 422 |
| `PUT …/settings` | `InventorySettings` | `InventoryView` | 422 |
| `PUT …/items/{item_id}/policy` | `ReorderPolicy` | `InventoryView` | 404, 422 |
| `POST …/closes/check` | `CloseCheckRequest` | `CloseCheckView` | 422 |
| `POST …/closes` | `CloseRequest` | 201 `CloseView` | 422 |

- [ ] **Step 1: 실패하는 테스트**

`backend/tests/test_api_inventory.py` 끝에 더한다:

```python
from decimal import Decimal as D

import pytest


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
    assert client.patch(f"{BASE}/items/it_none", json={"name": "x"}).status_code == 404
    assert client.patch(f"{BASE}/suppliers/sup_none", json={"name": "x"}).status_code == 404
    policy = {"min_stock": "1", "target_stock": "1", "purchase_unit": "1", "lead_days": 1, "unit_price": "0"}
    assert client.put(f"{BASE}/items/it_none/policy", json=policy).status_code == 404


def test_other_owner_sees_nothing_and_cannot_touch(client):
    fabric = _ids(_bulk(client, {"name": "원단", "kind": "material", "unit": "m"}).json())[0]
    other = api_client(client.app, client_id=OTHER_CLIENT_ID)

    assert other.get(BASE).json()["items"] == []
    assert other.patch(f"{BASE}/items/{fabric}", json={"name": "남의 것"}).status_code == 404
    assert client.get(BASE).json()["items"][0]["item"]["name"] == "원단"


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
    from app.inventory import service

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
```

- [ ] **Step 2: 실패 확인**

Run: `uv run --directory backend pytest tests/test_api_inventory.py -q`
Expected: 새 테스트가 FAIL(404 — 경로가 없다)

- [ ] **Step 3: 구현**

`backend/app/schemas/inventory.py`에 응답 모델을 더한다(import: `datetime`, `Decimal`, `ContractModel`, `Close`, `InventorySettings`, `Item`, `ReorderPolicy`, `Supplier`, `Anomaly`, `StockStatus`):

```python
class ItemView(ContractModel):
    item: Item
    on_hand: Decimal | None  # None = 미입력
    in_transit: Decimal
    status: StockStatus
    suggested_quantity: Decimal | None  # 부족할 때만. 제작 품목이면 '제작 필요' 수량
    policy: ReorderPolicy | None
    last_counted_at: datetime | None


class InventoryView(ContractModel):
    items: list[ItemView]  # 숨긴 품목 포함(item.archived). 화면이 거른다
    suppliers: list[Supplier]
    settings: InventorySettings
    last_close: Close | None


class CloseCheckView(ContractModel):
    anomalies: list[Anomaly]


class CloseView(ContractModel):
    close: Close
    inventory: InventoryView
```

`backend/app/inventory/views.py`:

```python
"""재고 상태 → 응답(순수). 수량·상태·제안량은 rules.py가 계산하고 화면은 다시 계산하지 않는다."""
from decimal import Decimal

from app.inventory.models import InventoryState, Item
from app.inventory.rules import item_status, last_counted_at, on_hand, suggested_quantity
from app.schemas.inventory import InventoryView, ItemView

_NOTHING_IN_TRANSIT = Decimal(0)  # 주문은 PR #41에서 생긴다. 그때 rules.in_transit(state.orders, item_id)로 바꾼다


def _item_view(state: InventoryState, item: Item) -> ItemView:
    quantity = on_hand(state.ledger, item.item_id)
    policy = state.policies.get(item.item_id)
    in_transit = _NOTHING_IN_TRANSIT
    return ItemView(
        item=item,
        on_hand=quantity,
        in_transit=in_transit,
        status=item_status(quantity, in_transit, policy),
        suggested_quantity=suggested_quantity(quantity, in_transit, policy),
        policy=policy,
        last_counted_at=last_counted_at(state.ledger, item.item_id),
    )


def to_inventory_view(state: InventoryState) -> InventoryView:
    return InventoryView(
        items=[_item_view(state, item) for item in state.items],
        suppliers=state.suppliers,
        settings=state.settings,
        last_close=state.closes[-1] if state.closes else None,
    )
```

`backend/app/api/inventory.py`를 채운다:

```python
"""재고 API. 상태 변경은 app/inventory/service.py, 응답은 app/inventory/views.py가 한다.

바꾸는 요청은 owner별 잠금 안에서 저장된 묶음의 복사본을 고치고, 끝까지 성공했을 때만 저장한다
(InventoryError·InventoryNotFound면 저장하지 않으므로 원자적이다). 묶음이 없으면 빈 묶음으로 시작한다.
"""
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import APIRouter

from app.api.deps import Inventories, InventoryLocks, Owner
from app.api.locks import SessionLocks
from app.api.responses import error_responses
from app.inventory import service
from app.inventory.models import InventorySettings, InventoryState, ReorderPolicy
from app.inventory.store import InventoryStore
from app.inventory.views import to_inventory_view
from app.schemas.inventory import (
    BulkItemsRequest,
    CloseCheckRequest,
    CloseCheckView,
    CloseRequest,
    CloseView,
    InventoryView,
    ItemDraft,
    ItemPatch,
    SupplierDraft,
    SupplierPatch,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], responses=error_responses(500))


def _load(store: InventoryStore, owner: str) -> InventoryState:
    return store.get(owner) or InventoryState(owner_id=owner)


@contextmanager
def _update(locks: SessionLocks, store: InventoryStore, owner: str) -> Iterator[InventoryState]:
    with locks.hold(owner):
        state = _load(store, owner)
        yield state
        store.save(state)


@router.get("", response_model=InventoryView, responses=error_responses(422))
def get_inventory(store: Inventories, owner: Owner) -> InventoryView:
    return to_inventory_view(_load(store, owner))


@router.post("/items/bulk", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_items(body: BulkItemsRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    """S01 일괄 등록. 전부 되거나 전부 안 된다."""
    with _update(locks, store, owner) as state:
        service.add_items(state, body.items)
    return to_inventory_view(state)


@router.post("/items", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_item(body: ItemDraft, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.add_items(state, [body])
    return to_inventory_view(state)


@router.patch("/items/{item_id}", response_model=InventoryView, responses=error_responses(404, 422))
def update_item(item_id: str, body: ItemPatch, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.update_item(state, item_id, body)
    return to_inventory_view(state)


@router.post("/suppliers", response_model=InventoryView, status_code=201, responses=error_responses(422))
def add_supplier(body: SupplierDraft, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.add_supplier(state, body)
    return to_inventory_view(state)


@router.patch("/suppliers/{supplier_id}", response_model=InventoryView, responses=error_responses(404, 422))
def update_supplier(
    supplier_id: str, body: SupplierPatch, store: Inventories, locks: InventoryLocks, owner: Owner
) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.update_supplier(state, supplier_id, body)
    return to_inventory_view(state)


@router.put("/settings", response_model=InventoryView, responses=error_responses(422))
def set_settings(body: InventorySettings, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_settings(state, body)
    return to_inventory_view(state)


@router.put("/items/{item_id}/policy", response_model=InventoryView, responses=error_responses(404, 422))
def set_policy(item_id: str, body: ReorderPolicy, store: Inventories, locks: InventoryLocks, owner: Owner) -> InventoryView:
    with _update(locks, store, owner) as state:
        service.set_policy(state, item_id, body)
    return to_inventory_view(state)


@router.post("/closes/check", response_model=CloseCheckView, responses=error_responses(422))
def check_close(body: CloseCheckRequest, store: Inventories, owner: Owner) -> CloseCheckView:
    """저장하지 않고 이상 수량만 돌려준다(S05-check)."""
    return CloseCheckView(anomalies=service.check_close(_load(store, owner), body.counts))


@router.post("/closes", response_model=CloseView, status_code=201, responses=error_responses(422))
def record_close(body: CloseRequest, store: Inventories, locks: InventoryLocks, owner: Owner) -> CloseView:
    with _update(locks, store, owner) as state:
        close = service.record_close(state, body)
    return CloseView(close=close, inventory=to_inventory_view(state))
```

주의: 테스트의 잠금 스파이는 `service.add_supplier`를 바꾸므로 라우터는 `from app.inventory import service`로 모듈을 불러 `service.add_supplier(...)`로 부른다(함수를 직접 import하지 않는다).

- [ ] **Step 4: 통과 확인**

Run: `uv run --directory backend pytest tests/test_api_inventory.py tests/test_contract.py -q`
Expected: 모두 PASS(`test_contract.py`가 새 응답 모델이 모두 required인지 확인한다. 실패하면 그 모델이 `ContractModel`을 상속하는지 본다)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/inventory/views.py backend/app/schemas/inventory.py backend/app/api/inventory.py backend/tests/test_api_inventory.py
git commit -m "재고 API: 조회·품목·거래처·설정·기준·하루 마감"
```

---

### Task 8: 전체 확인·생성물·문서

**Files:**
- Modify: `frontend/openapi.json`, `frontend/src/api/schema.d.ts`(생성물), `CLAUDE.md`, `docs/HANDOFF.md`, `docs/WBS.xlsx`

- [ ] **Step 1: 백엔드 전체 테스트**

Run: `uv run --directory backend pytest -q`
Expected: 모두 PASS. 통과 수를 적어 둔다(HANDOFF에 쓴다).

- [ ] **Step 2: 프론트 타입 다시 만들기·빌드**

Run: `npm --prefix frontend run gen:api` 그다음 `npm --prefix frontend run build` 그다음 `npm --prefix frontend test`
Expected: 빌드·테스트 PASS(재고 화면은 아직 없으므로 새 타입은 쓰이지 않는다). 통과 수를 적어 둔다.

- [ ] **Step 3: CLAUDE.md 구조에 재고를 더한다**

`## 구조`의 `backend/app/schemas/` 줄 앞에 한 줄 더한다:

```markdown
- `backend/app/inventory/` — 재고 관리(코칭과 별개 업무 기능, 설계 `docs/superpowers/specs/2026-11-08-inventory-design.md`). owner마다 묶음 하나(`InventoryState`, JSON 문서 하나)이고 수량은 저장하지 않고 원장(`count`·`adjust`)에서 계산한다(`rules.py`, 순수: 보유 = 마지막 실사 + 그 뒤 조정, 미입력 ≠ 0, 상태·제안 주문량(구매 단위로 올림)·이상 수량). 상태 변경은 `service.py` 한 곳(규칙 위반 `InventoryError` 422, 없는 품목·거래처 `InventoryNotFound` 404), 응답은 `views.py`(순수), 저장소는 `store.py`(메모리·SQLite·Postgres `inventories` 표, 계약 `tests/test_inventory_store_contract.py`, `build_storage`가 `STORE`로 함께 만든다). 라우터 `app/api/inventory.py`(`/api/v1/inventory`)는 owner별 잠금(`app.state.inventory_locks`) 안에서 복사본을 고치고 성공해야 저장한다(원자적). 원장 기록이 있는 품목은 단위를 못 바꾼다.
```

- [ ] **Step 4: HANDOFF·WBS**

- `docs/HANDOFF.md`: 기준일 2026-11-08, 테스트 수(Step 1·2), "지금 상태" 표에 `| 재고 관리 핵심 | #40 | 설계(`docs/superpowers/specs/2026-11-08-inventory-design.md`)·IA 원본(`design/2026-11-05-ia-inventory-proposal/`), owner별 재고 묶음, 원장 기반 수량, 품목·거래처·설정·보충 기준·하루 마감(이상 수량 확인) API |` 행을 더한다. "다음 할 일" 맨 위에 "재고 관리 묶음: #41 주문·자동 주문·AI 기준 추천 → #42·#43 화면(디자인은 기능을 더 발전시킨 뒤 받는다)"를 적는다. main 해시는 머지 뒤에 고친다.
- WBS(저장소 루트에서):

```bash
uv run --no-project --with openpyxl python scripts/wbs.py add 4.12 "재고 관리 핵심(모델·원장·품목·하루 마감 API)" --after 4.11 --owner 개발 --start 2026-11-08 --status "진행 중" --pct 0.5
uv run --no-project --with openpyxl python scripts/wbs.py add 4.13 "재고 주문·자동 주문·AI 기준 추천" --after 4.12 --owner 개발 --status 예정
uv run --no-project --with openpyxl python scripts/wbs.py add 4.14 "재고 화면 1(현황·마감·품목·기준)" --after 4.13 --owner 개발 --status 예정
uv run --no-project --with openpyxl python scripts/wbs.py add 4.15 "재고 화면 2(주문·입고·보류·자동 주문·미리보기)" --after 4.14 --owner 개발 --status 예정
uv run --no-project --with openpyxl python scripts/wbs.py date 2026-11-08
```

`--owner`·`--status` 허용값은 `scripts/wbs.py --help`로 확인한다. PR을 연 뒤 머지할 때 `set 4.12 --status 완료 --end <날짜> --pct 1 --output "PR #40"`.

- [ ] **Step 5: 커밋**

```bash
git add CLAUDE.md docs/HANDOFF.md docs/WBS.xlsx frontend/openapi.json frontend/src/api/schema.d.ts
git commit -m "재고 핵심: 문서·WBS·프론트 API 타입 갱신"
```

푸시와 PR은 사용자가 요청할 때 한다.
