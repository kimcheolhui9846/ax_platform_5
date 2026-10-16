from pathlib import Path

import app.config as config
from app.config import Settings

BACKEND_DIR = Path(config.__file__).resolve().parents[1]


def test_env_file_is_anchored_to_backend_folder():
    """실행 위치(CWD)와 상관없이 backend/.env를 읽는다."""
    assert Path(Settings.model_config["env_file"]) == BACKEND_DIR / ".env"


def test_debug_defaults_to_false(monkeypatch):
    """trace 엔드포인트는 DEBUG=true로 켤 때만 열린다(.env.example이 로컬 개발용으로 켠다)."""
    monkeypatch.delenv("DEBUG", raising=False)
    assert Settings(_env_file=None).debug is False
