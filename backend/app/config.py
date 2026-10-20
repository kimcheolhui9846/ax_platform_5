"""환경 설정. backend/.env 또는 환경 변수에서 읽는다. 실행 위치와 상관없이 backend/.env를 본다."""
import json
from pathlib import Path
from typing import Annotated

from psycopg.conninfo import conninfo_to_dict
from pydantic import NonNegativeFloat, PositiveInt, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.core.store import StoreKind
from app.providers.routing import ROUTABLE_STAGES, Effort

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
DEFAULT_DATABASE_PATH = BACKEND_DIR / "data" / "sessions.db"
DEFAULT_ASSET_DIR = BACKEND_DIR / "data" / "assets"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True)  # 오류에 입력 값(DATABASE_URL)을 싣지 않는다

    provider: str = "mock"
    claude_model: str = "claude-opus-5-5"  # PROVIDER=claude일 때 쓰는 모델
    claude_effort: Effort = "medium"  # 생각 깊이·비용
    # 단계별 라우팅(기본 꺼짐). JSON 객체. 예: CLAUDE_STAGE_MODELS={"diagnose":"claude-haiku-5-5"}
    claude_stage_models: Annotated[dict[str, str], NoDecode] = {}
    claude_stage_efforts: Annotated[dict[str, Effort], NoDecode] = {}
    image_provider: str = "mock"
    # AI 동시 호출 상한(LLM·이미지 합쳐서). 자리를 이 시간 안에 못 얻으면 503. app/providers/limit.py
    ai_max_concurrent_calls: PositiveInt = 4
    ai_queue_wait_seconds: NonNegativeFloat = 10
    debug: bool = False  # true면 trace 엔드포인트를 연다. 로컬 개발은 .env.example대로 켠다.
    store: StoreKind = "memory"  # sqlite면 DATABASE_PATH 파일에 세션을 남긴다(서버를 다시 켜도 남는다)
    database_path: Path = DEFAULT_DATABASE_PATH
    asset_dir: Path = DEFAULT_ASSET_DIR  # sqlite 저장소일 때 결과 이미지를 두는 폴더
    database_url: SecretStr | None = None  # STORE=postgres일 때 접속 주소(비밀 값: 오류·로그에 싣지 않는다)

    @model_validator(mode="after")
    def _postgres_needs_url(self) -> "Settings":
        if self.store == "postgres" and (self.database_url is None or not self.database_url.get_secret_value()):
            raise ValueError("STORE=postgres에는 DATABASE_URL이 필요합니다.")
        return self

    @model_validator(mode="after")
    def _database_url_format(self) -> "Settings":
        """접속 주소 형식만 본다(연결하지 않는다). 오류에는 주소를 싣지 않는다(필드 검증기는 입력 값을 오류에 싣는다)."""
        if self.database_url is None or not self.database_url.get_secret_value():
            return self
        try:
            conninfo_to_dict(self.database_url.get_secret_value())
        except Exception:
            raise ValueError("DATABASE_URL 형식이 올바르지 않습니다.") from None
        return self

    @field_validator("claude_stage_models", "claude_stage_efforts", mode="before")
    @classmethod
    def _parse_json(cls, value: object, info: ValidationInfo) -> object:
        """환경 변수 문자열을 JSON 객체로 읽는다. 빈 문자열(`CLAUDE_STAGE_MODELS=`)은 꺼짐({})이다."""
        if not isinstance(value, str):
            return value
        if not value.strip():
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{info.field_name.upper()}는 JSON 객체여야 합니다: {exc.msg}") from exc

    @field_validator("claude_stage_models", "claude_stage_efforts")
    @classmethod
    def _known_stages(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(value) - set(ROUTABLE_STAGES))
        if unknown:
            raise ValueError(
                f"라우팅할 수 없는 단계입니다: {', '.join(unknown)} (가능: {', '.join(ROUTABLE_STAGES)})"
            )
        return value


settings = Settings()
