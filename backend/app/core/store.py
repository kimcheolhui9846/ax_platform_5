"""세션 저장소. 메모리(테스트·임시)와 SQLite(서버를 다시 켜도 남는다) 두 가지다.

계약은 tests/test_store_contract.py가 두 구현 모두에 대해 확인한다.
"""
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Literal, Protocol

from app.core.results import utcnow
from app.core.state import SessionState

StoreKind = Literal["memory", "sqlite"]


class SessionStore(Protocol):
    """저장소 계약.

    - get은 복사본을 돌려준다. 받은 객체를 바꿔도 저장된 값은 그대로다. 없는 id면 None.
    - save는 복사본을 저장한다. 저장 뒤 원래 객체를 바꿔도 새지 않는다. 저장할 때 updated_at을 지금으로 바꾼다.
    - list_by_owner는 그 사용자의 세션 복사본을 최근에 저장한 순서로 돌려준다. 목록은 요약만 쓰므로 무거운
      trace(단계별 프롬프트·응답)는 빼고 읽는다(get은 그대로 준다).
    - list_all은 모든 사용자의 세션을 같은 방식(최근 순서, trace 없음)으로 돌려준다. 평가 통계(scripts/session_stats.py)만 쓴다.
    """

    def get(self, session_id: str) -> SessionState | None: ...

    def save(self, state: SessionState) -> None: ...

    def list_by_owner(self, owner_id: str) -> list[SessionState]: ...

    def list_all(self) -> list[SessionState]: ...


class InMemorySessionStore:
    """서버를 재시작하면 사라진다. 테스트의 기본값이다."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState | None:
        state = self._sessions.get(session_id)
        return state.model_copy(deep=True) if state else None

    def save(self, state: SessionState) -> None:
        state.updated_at = utcnow()
        self._sessions[state.session_id] = state.model_copy(deep=True)

    def list_by_owner(self, owner_id: str) -> list[SessionState]:
        return self._listed([s for s in self._sessions.values() if s.owner_id == owner_id])

    def list_all(self) -> list[SessionState]:
        return self._listed(list(self._sessions.values()))

    @staticmethod
    def _listed(states: list[SessionState]) -> list[SessionState]:
        newest = sorted(states, key=lambda s: s.updated_at, reverse=True)
        return [s.model_copy(update={"trace": []}).model_copy(deep=True) for s in newest]


_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_by_owner ON sessions (owner_id, updated_at);
"""


class SqliteSessionStore:
    """표 하나에 세션 JSON을 둔다(owner_id·updated_at은 목록을 위해 따로 둔다).

    요청마다 연결을 열고 닫으므로 스레드 풀에서 돌아도 안전하다. 같은 세션의 읽기→저장은 세션별 잠금
    (app/api/locks.py)이 하나로 묶으므로 서버 프로세스는 하나만 띄운다.
    """

    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._path = path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """연결 하나에 트랜잭션 하나. 끝나면 커밋(예외면 롤백)하고 닫는다."""
        with closing(sqlite3.connect(self._path)) as conn:
            with conn:
                yield conn

    def get(self, session_id: str) -> SessionState | None:
        with self._connect() as conn:
            row = conn.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return SessionState.model_validate_json(row[0]) if row else None

    def save(self, state: SessionState) -> None:
        state.updated_at = utcnow()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, owner_id, updated_at, data) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                "owner_id = excluded.owner_id, updated_at = excluded.updated_at, data = excluded.data",
                (state.session_id, state.owner_id, state.updated_at.isoformat(), state.model_dump_json()),
            )

    def list_by_owner(self, owner_id: str) -> list[SessionState]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT json_remove(data, '$.trace') FROM sessions WHERE owner_id = ? ORDER BY updated_at DESC",
                (owner_id,),
            ).fetchall()
        return [SessionState.model_validate_json(row[0]) for row in rows]

    def list_all(self) -> list[SessionState]:
        with self._connect() as conn:
            rows = conn.execute("SELECT json_remove(data, '$.trace') FROM sessions ORDER BY updated_at DESC").fetchall()
        return [SessionState.model_validate_json(row[0]) for row in rows]


def build_store(kind: StoreKind, path: Path) -> SessionStore:
    """설정(STORE·DATABASE_PATH)으로 저장소를 고른다."""
    return SqliteSessionStore(path) if kind == "sqlite" else InMemorySessionStore()
