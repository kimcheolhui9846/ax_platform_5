"""환경 설정. backend/.env 또는 환경 변수에서 읽는다. 실행 위치와 상관없이 backend/.env를 본다."""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.store import StoreKind

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_DATABASE_PATH = BACKEND_DIR / "data" / "sessions.db"
DEFAULT_ASSET_DIR = BACKEND_DIR / "data" / "assets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    provider: str = "mock"
    claude_model: str = "claude-opus-5-5"  # PROVIDER=claude일 때 쓰는 모델
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"  # 생각 깊이·비용
    image_provider: str = "mock"
    debug: bool = False  # true면 trace 엔드포인트를 연다. 로컬 개발은 .env.example대로 켠다.
    store: StoreKind = "memory"  # sqlite면 DATABASE_PATH 파일에 세션을 남긴다(서버를 다시 켜도 남는다)
    database_path: Path = DEFAULT_DATABASE_PATH
    asset_dir: Path = DEFAULT_ASSET_DIR  # sqlite 저장소일 때 결과 이미지를 두는 폴더


settings = Settings()
