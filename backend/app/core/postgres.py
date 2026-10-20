"""Postgres 세션·결과 이미지 저장소(Neon 같은 관리형 Postgres용). 계약은 store.py·assets.py의 Protocol과 같다.

연결 풀 하나를 두 저장소가 나눠 쓴다. 접속 주소는 비밀 값이라 오류·로그에 싣지 않는다.
"""
from psycopg_pool import ConnectionPool

from app.core.assets import ASSET_ID_PATTERN, Asset, new_asset_id
from app.core.results import utcnow
from app.core.state import SessionState

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    data JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_by_owner ON sessions (owner_id, updated_at DESC);
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    mime TEXT NOT NULL,
    data BYTEA NOT NULL
);
"""


def open_pool(url: str) -> ConnectionPool:
    """풀을 열고 표가 없으면 만든다. 풀러(pgbouncer)와 맞도록 서버 측 준비 문을 끈다."""
    pool = ConnectionPool(
        url,
        min_size=1,
        max_size=4,
        kwargs={"prepare_threshold": None, "autocommit": True},
        check=ConnectionPool.check_connection,  # 꺼낼 때 죽은 연결(Neon이 쉬는 동안 끊김)을 걸러 새로 연다
        max_idle=240,
        max_lifetime=1800,
        open=False,
    )
    try:
        pool.open(wait=True, timeout=15)  # 관리형 DB가 자다 깨는 첫 연결은 몇 초 걸릴 수 있다
        with pool.connection() as conn:
            conn.execute(_SCHEMA)
    except Exception:
        pool.close()
        raise
    return pool


class PostgresSessionStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def get(self, session_id: str) -> SessionState | None:
        with self._pool.connection() as conn:
            row = conn.execute("SELECT data::text FROM sessions WHERE session_id = %s", (session_id,)).fetchone()
        return SessionState.model_validate_json(row[0]) if row else None

    def save(self, state: SessionState) -> None:
        state.updated_at = utcnow()
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, owner_id, updated_at, data) VALUES (%s, %s, %s, %s::jsonb) "
                "ON CONFLICT (session_id) DO UPDATE SET "
                "owner_id = EXCLUDED.owner_id, updated_at = EXCLUDED.updated_at, data = EXCLUDED.data",
                (state.session_id, state.owner_id, state.updated_at, state.model_dump_json()),
            )

    def list_by_owner(self, owner_id: str) -> list[SessionState]:
        with self._pool.connection() as conn:
            rows = conn.execute(
                "SELECT (data - 'trace')::text FROM sessions WHERE owner_id = %s ORDER BY updated_at DESC",
                (owner_id,),
            ).fetchall()
        return [SessionState.model_validate_json(row[0]) for row in rows]

    def list_all(self) -> list[SessionState]:
        with self._pool.connection() as conn:
            rows = conn.execute("SELECT (data - 'trace')::text FROM sessions ORDER BY updated_at DESC").fetchall()
        return [SessionState.model_validate_json(row[0]) for row in rows]

    def delete(self, session_id: str) -> None:
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = %s", (session_id,))


class PostgresAssetStore:
    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def put(self, owner_id: str, data: bytes, mime: str) -> str:
        asset_id = new_asset_id(mime)
        with self._pool.connection() as conn:
            conn.execute(
                "INSERT INTO assets (asset_id, owner_id, mime, data) VALUES (%s, %s, %s, %s)",
                (asset_id, owner_id, mime, data),
            )
        return asset_id

    def get(self, asset_id: str) -> Asset | None:
        if not ASSET_ID_PATTERN.fullmatch(asset_id):
            return None
        with self._pool.connection() as conn:
            row = conn.execute("SELECT owner_id, mime, data FROM assets WHERE asset_id = %s", (asset_id,)).fetchone()
        return Asset(owner_id=row[0], mime=row[1], data=bytes(row[2])) if row else None

    def delete(self, asset_id: str) -> None:
        if not ASSET_ID_PATTERN.fullmatch(asset_id):
            return
        with self._pool.connection() as conn:
            conn.execute("DELETE FROM assets WHERE asset_id = %s", (asset_id,))
