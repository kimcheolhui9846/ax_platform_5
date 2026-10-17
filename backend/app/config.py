"""환경 설정. backend/.env 또는 환경 변수에서 읽는다. 실행 위치와 상관없이 backend/.env를 본다."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.store import StoreKind

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_DATABASE_PATH = BACKEND_DIR / "data" / "sessions.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    provider: str = "mock"
    debug: bool = False  # true면 trace 엔드포인트를 연다. 로컬 개발은 .env.example대로 켠다.
    store: StoreKind = "memory"  # sqlite면 DATABASE_PATH 파일에 세션을 남긴다(서버를 다시 켜도 남는다)
    database_path: Path = DEFAULT_DATABASE_PATH


settings = Settings()
