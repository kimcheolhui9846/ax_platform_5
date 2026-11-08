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
        # 늦게 불러온다: app.core.postgres는 모듈 맨 위에서 psycopg_pool을 불러오므로,
        # Postgres를 안 쓰는 경로(메모리·SQLite)가 이 모듈만 가져와도 psycopg가 필요해지지 않게 한다.
        from app.core.postgres import without_nul

        state.updated_at = utcnow()
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO inventories (owner_id, updated_at, data) VALUES (%s, %s, %s::jsonb) "
                "ON CONFLICT (owner_id) DO UPDATE SET updated_at = EXCLUDED.updated_at, data = EXCLUDED.data",
                (state.owner_id, state.updated_at, without_nul(state.model_dump_json())),
            )
