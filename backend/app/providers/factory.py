"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 여기에 한 줄씩 추가한다."""
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


def get_provider(name: str) -> LLMProvider:
    if name == "mock":
        return MockProvider()
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: mock)")
