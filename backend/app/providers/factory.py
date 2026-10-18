"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 여기에 한 줄씩 추가한다."""
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider

DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"
DEFAULT_CLAUDE_EFFORT = "medium"


def get_provider(name: str, *, model: str = DEFAULT_CLAUDE_MODEL, effort: str = DEFAULT_CLAUDE_EFFORT) -> LLMProvider:
    if name == "mock":
        return MockProvider()
    if name == "claude":
        from app.providers.claude import ClaudeProvider  # mock만 쓸 때는 SDK를 읽지 않는다

        return ClaudeProvider(model=model, effort=effort)
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: mock, claude)")
