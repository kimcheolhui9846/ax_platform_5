"""저장소 고르기 한 곳. 세션 저장소와 결과 이미지 저장소를 STORE에 맞춰 짝으로 만든다."""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.core.assets import AssetStore, InMemoryAssetStore, LocalAssetStore
from app.core.store import InMemorySessionStore, SessionStore, SqliteSessionStore, StoreKind


@dataclass(frozen=True)
class Storage:
    sessions: SessionStore
    assets: AssetStore
    close: Callable[[], None]  # 앱이 끝날 때 부른다(Postgres 연결 풀을 닫는다)


def _nothing() -> None:
    pass


def opens_connections(kind: StoreKind) -> bool:
    """이 저장소를 만들면 연결 풀 같은 자원이 열리는가. 열리면 서버가 시작할 때 만들고 끝날 때 닫는다."""
    return kind == "postgres"


def build_storage(kind: StoreKind, database_path: Path, asset_dir: Path, database_url: str | None) -> Storage:
    """memory: 둘 다 메모리. sqlite: 세션 파일 + 이미지 폴더. postgres: 풀 하나를 둘이 나눠 쓴다."""
    if kind == "postgres":
        if not database_url:
            raise ValueError("STORE=postgres에는 DATABASE_URL이 필요합니다.")
        from app.core.postgres import PostgresAssetStore, PostgresSessionStore, open_pool

        pool = open_pool(database_url)
        return Storage(PostgresSessionStore(pool), PostgresAssetStore(pool), pool.close)
    if kind == "sqlite":
        return Storage(SqliteSessionStore(database_path), LocalAssetStore(asset_dir), _nothing)
    return Storage(InMemorySessionStore(), InMemoryAssetStore(), _nothing)
