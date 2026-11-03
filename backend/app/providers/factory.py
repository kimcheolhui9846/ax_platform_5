"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 BUILDERS에 한 줄씩 추가한다.

base_url·api_key는 게이트웨이(예: BAZE)를 거칠 때 쓴다. 없으면 각 SDK가 환경 변수와 공식 주소를 쓴다.
"""
from collections.abc import Callable, Mapping

from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.routing import RoutedProvider, stage_targets

DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"
DEFAULT_CLAUDE_EFFORT = "medium"
SUPPORTED = ("mock", "claude", "openai")


def _builder(name: str, base_url: str | None, api_key: str | None) -> Callable[[str, str], LLMProvider]:
    """(모델, 노력) → 제공자. SDK는 쓰는 제공자만 읽는다(mock만 쓸 때는 읽지 않는다)."""
    if name == "claude":
        from app.providers.claude import ClaudeProvider

        return lambda model, effort: ClaudeProvider(model=model, effort=effort, base_url=base_url, api_key=api_key)
    if name == "openai":
        from app.providers.openai_chat import OpenAIProvider

        return lambda model, effort: OpenAIProvider(model=model, effort=effort, base_url=base_url, api_key=api_key)
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: {', '.join(SUPPORTED)})")


def get_provider(
    name: str,
    *,
    model: str = DEFAULT_CLAUDE_MODEL,
    effort: str = DEFAULT_CLAUDE_EFFORT,
    stage_models: Mapping[str, str] | None = None,
    stage_efforts: Mapping[str, str] | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    if name == "mock":
        return MockProvider()  # 비용 0. 단계 설정은 보지 않는다
    build = _builder(name, base_url, api_key)
    default = build(model, effort)
    targets = stage_targets(model, effort, stage_models or {}, stage_efforts or {})
    if not targets:
        return default
    built: dict[tuple[str, str], LLMProvider] = {(model, effort): default}
    for target in targets.values():
        if target not in built:
            built[target] = build(*target)
    return RoutedProvider(default, {stage: built[target] for stage, target in targets.items()})
