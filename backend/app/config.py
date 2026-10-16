"""환경 설정. backend/.env 또는 환경 변수에서 읽는다. 실행 위치와 상관없이 backend/.env를 본다."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    provider: str = "mock"
    debug: bool = False  # true면 trace 엔드포인트를 연다. 로컬 개발은 .env.example대로 켠다.


settings = Settings()
