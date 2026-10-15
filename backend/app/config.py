"""환경 설정. backend/.env 또는 환경 변수에서 읽는다."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider: str = "mock"
    debug: bool = True


settings = Settings()
