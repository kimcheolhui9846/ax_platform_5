from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

import app.config as config
from app.core.state import SessionState
from app.config import Settings
from app.core.assets import InMemoryAssetStore, LocalAssetStore
from app.core.storage import build_storage
from app.core.store import InMemorySessionStore, SqliteSessionStore

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


def test_build_storage_picks_the_kind(tmp_path):
    memory = build_storage("memory", tmp_path / "x.db", tmp_path / "assets", None)
    assert isinstance(memory.sessions, InMemorySessionStore) and isinstance(memory.assets, InMemoryAssetStore)
    sqlite = build_storage("sqlite", tmp_path / "x.db", tmp_path / "assets", None)
    assert isinstance(sqlite.sessions, SqliteSessionStore) and isinstance(sqlite.assets, LocalAssetStore)
    memory.close()
    sqlite.close()


def test_build_storage_postgres_shares_one_pool_and_closes_it(_postgres_url, tmp_path):
    from app.core.postgres import PostgresAssetStore, PostgresSessionStore

    storage = build_storage("postgres", tmp_path / "x.db", tmp_path / "assets", _postgres_url)
    assert isinstance(storage.sessions, PostgresSessionStore) and isinstance(storage.assets, PostgresAssetStore)
    pool = storage.sessions._pool
    assert storage.assets._pool is pool and pool.closed  # 만들 때는 연결하지 않는다
    storage.open()
    assert not pool.closed
    storage.close()
    assert pool.closed


def test_build_storage_postgres_without_url_fails_without_leaking(tmp_path):
    with pytest.raises(ValueError, match="DATABASE_URL"):
        build_storage("postgres", tmp_path / "x.db", tmp_path / "assets", None)


def test_postgres_store_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError, match="STORE=postgres에는 DATABASE_URL이 필요합니다."):
        Settings(_env_file=None, store="postgres")


def test_database_url_is_secret(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    url = "postgresql://user:hunter2secret@host/db"
    settings = Settings(_env_file=None, store="postgres", database_url=url)
    assert "hunter2secret" not in repr(settings) and "hunter2secret" not in str(settings)
    assert settings.database_url.get_secret_value() == url
    with pytest.raises(ValidationError) as excinfo:
        Settings(_env_file=None, store="postgres", database_url="")
    assert "hunter2secret" not in str(excinfo.value)


def test_create_app_on_postgres_keeps_sessions(_postgres_url, postgres_pool, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setattr(config.settings, "store", "postgres")
    monkeypatch.setattr(config.settings, "database_url", SecretStr(_postgres_url))
    app = create_app()
    pool = app.state.store._pool
    assert pool.closed  # 서버가 시작하기 전에는 풀을 열지 않는다(연결 없음)
    with TestClient(app) as client:
        state = SessionState(session_id="s-pg", owner_id="o", task_type="business_plan", raw_input="x")
        app.state.store.save(state)
        assert app.state.store.get("s-pg").owner_id == "o"
        assert not pool.closed
    assert pool.closed


def test_tests_never_touch_a_real_database():
    """conftest가 개발자 .env(STORE=sqlite)와 상관없이 메모리 저장소로 정한다(테스트 세션이 실제 DB에 쌓이지 않게)."""
    from app.main import create_app

    assert config.settings.store == "memory"
    assert isinstance(create_app().state.store, InMemorySessionStore)


def test_stage_settings_default_empty(monkeypatch):
    monkeypatch.delenv("CLAUDE_STAGE_MODELS", raising=False)
    monkeypatch.delenv("CLAUDE_STAGE_EFFORTS", raising=False)
    settings = Settings(_env_file=None)
    assert settings.claude_stage_models == {} and settings.claude_stage_efforts == {}


def test_stage_settings_read_json_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_STAGE_MODELS", '{"diagnose": "claude-haiku-5-5"}')
    monkeypatch.setenv("CLAUDE_STAGE_EFFORTS", '{"generate": "high"}')
    settings = Settings(_env_file=None)
    assert settings.claude_stage_models == {"diagnose": "claude-haiku-5-5"}
    assert settings.claude_stage_efforts == {"generate": "high"}


@pytest.mark.parametrize("name", ["CLAUDE_STAGE_MODELS", "CLAUDE_STAGE_EFFORTS"])
@pytest.mark.parametrize("empty", ["", "   "])
def test_empty_stage_env_means_off(monkeypatch, name, empty):
    monkeypatch.setenv(name, empty)
    settings = Settings(_env_file=None)
    assert settings.claude_stage_models == {} and settings.claude_stage_efforts == {}


def test_bad_json_stage_env_is_an_error(monkeypatch):
    monkeypatch.setenv("CLAUDE_STAGE_MODELS", "{not json")
    with pytest.raises(Exception, match="CLAUDE_STAGE_MODELS|JSON|json"):
        Settings(_env_file=None)


@pytest.mark.parametrize("bad", [{"generat": "claude-haiku-5-5"}, {"image": "claude-haiku-5-5"}])
def test_unknown_stage_names_are_rejected(bad):
    with pytest.raises(ValidationError, match="diagnose"):  # 메시지에 허용 단계 이름이 있다
        Settings(_env_file=None, claude_stage_models=bad)


def test_bad_effort_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, claude_stage_efforts={"generate": "ultra"})
    with pytest.raises(ValidationError):
        Settings(_env_file=None, claude_stage_efforts={"imagee": "low"})


def test_ai_call_limit_defaults(monkeypatch):
    monkeypatch.delenv("AI_MAX_CONCURRENT_CALLS", raising=False)
    monkeypatch.delenv("AI_QUEUE_WAIT_SECONDS", raising=False)
    settings = Settings(_env_file=None)
    assert (settings.ai_max_concurrent_calls, settings.ai_queue_wait_seconds) == (4, 10)


@pytest.mark.parametrize(("name", "value"), [("AI_MAX_CONCURRENT_CALLS", "0"), ("AI_QUEUE_WAIT_SECONDS", "-1")])
def test_ai_call_limit_rejects_out_of_range(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
