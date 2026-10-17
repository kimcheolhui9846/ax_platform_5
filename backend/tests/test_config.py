from pathlib import Path

import app.config as config
from app.config import Settings
from app.core.store import InMemorySessionStore, SqliteSessionStore, build_store

BACKEND_DIR = Path(config.__file__).resolve().parents[1]


def test_env_file_is_anchored_to_backend_folder():
    """실행 위치(CWD)와 상관없이 backend/.env를 읽는다."""
    assert Path(Settings.model_config["env_file"]) == BACKEND_DIR / ".env"


def test_debug_defaults_to_false(monkeypatch):
    """trace 엔드포인트는 DEBUG=true로 켤 때만 열린다(.env.example이 로컬 개발용으로 켠다)."""
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).debug is False


def test_store_defaults_to_memory(monkeypatch):
    """테스트는 결정적이도록 메모리 저장소가 기본이다(.env.example이 로컬 개발용으로 sqlite를 켠다)."""
    monkeypatch.delenv("STORE", raising=False)
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    settings = Settings(_env_file=None)
    assert settings.store == "memory"
    assert settings.database_path == BACKEND_DIR / "data" / "sessions.db"


def test_build_store_picks_the_kind(tmp_path):
    assert isinstance(build_store("memory", tmp_path / "x.db"), InMemorySessionStore)
    assert isinstance(build_store("sqlite", tmp_path / "x.db"), SqliteSessionStore)


def test_tests_never_touch_a_real_database():
    """conftest가 개발자 .env(STORE=sqlite)와 상관없이 메모리 저장소로 정한다(테스트 세션이 실제 DB에 쌓이지 않게)."""
    from app.main import create_app

    assert config.settings.store == "memory"
    assert isinstance(create_app().state.store, InMemorySessionStore)
