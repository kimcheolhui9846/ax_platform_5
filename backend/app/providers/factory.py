"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 여기에 한 줄씩 추가한다."""
from collections.abc import Mapping

from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.routing import RoutedProvider, stage_targets

DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"
DEFAULT_CLAUDE_EFFORT = "medium"


def get_provider(
    name: str,
    *,
    model: str = DEFAULT_CLAUDE_MODEL,
    effort: str = DEFAULT_CLAUDE_EFFORT,
    stage_models: Mapping[str, str] | None = None,
    stage_efforts: Mapping[str, str] | None = None,
) -> LLMProvider:
    if name == "mock":
        return MockProvider()  # 비용 0. 단계 설정은 보지 않는다
    if name == "claude":
        from app.providers.claude import ClaudeProvider  # mock만 쓸 때는 SDK를 읽지 않는다

        default = ClaudeProvider(model=model, effort=effort)
        targets = stage_targets(model, effort, stage_models or {}, stage_efforts or {})
        if not targets:
            return default
        built: dict[tuple[str, str], LLMProvider] = {(model, effort): default}
        for target in targets.values():
            if target not in built:
                built[target] = ClaudeProvider(model=target[0], effort=target[1])
        return RoutedProvider(default, {stage: built[target] for stage, target in targets.items()})
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: mock, claude)")
