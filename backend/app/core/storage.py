"""저장소 고르기 한 곳. 세션 저장소와 결과 이미지 저장소를 STORE에 맞춰 짝으로 만든다."""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.assets import AssetStore, InMemoryAssetStore, LocalAssetStore
from app.core.state import SessionState
from app.core.store import InMemorySessionStore, SessionStore, SqliteSessionStore, StoreKind


@dataclass(frozen=True)
class Storage:
    sessions: SessionStore
    assets: AssetStore
    open: Callable[[], None]  # 서버가 시작할 때 부른다(Postgres는 연결 풀을 열고 표를 만든다). 닫은 뒤 다시 열 수 없다(psycopg 풀): 수명 하나에 앱 인스턴스 하나
    close: Callable[[], None]  # 서버가 끝날 때 부른다(Postgres 연결 풀을 닫는다)


def _nothing() -> None:
    pass


def build_storage(kind: StoreKind, database_path: Path, asset_dir: Path, database_url: str | None) -> Storage:
    """memory: 둘 다 메모리. sqlite: 세션 파일 + 이미지 폴더. postgres: 풀 하나를 둘이 나눠 쓴다. 연결은 open()에서 한다."""
    if kind == "postgres":
        if not database_url:
            raise ValueError("STORE=postgres에는 DATABASE_URL이 필요합니다.")
        from app.core.postgres import PostgresAssetStore, PostgresSessionStore, make_pool, open_pool

        pool = make_pool(database_url)
        return Storage(PostgresSessionStore(pool), PostgresAssetStore(pool), lambda: open_pool(pool), pool.close)
    if kind == "sqlite":
        return Storage(SqliteSessionStore(database_path), LocalAssetStore(asset_dir), _nothing, _nothing)
    return Storage(InMemorySessionStore(), InMemoryAssetStore(), _nothing, _nothing)


def read_all_sessions(kind: StoreKind, database_path: Path, asset_dir: Path, database_url: str | None) -> list[SessionState]:
    """저장소를 열어 모든 세션을 읽고 닫는다(평가 통계용 한 번 읽기)."""
    storage = build_storage(kind, database_path, asset_dir, database_url)
    try:
        storage.open()
        return storage.sessions.list_all()
    finally:
        storage.close()
