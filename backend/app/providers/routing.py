"""단계별 모델 라우팅. 하네스는 그대로 단계 이름을 넘기고, 어느 모델이 답할지는 여기서 정한다.

설정이 없으면 쓰지 않는다(factory가 감싸지 않는다). 고르기는 순수 함수, RoutedProvider는 넘기기만 한다.
로드맵: docs/HARNESS-ROADMAP.md 3장.
"""
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from app.providers.base import LLMProvider, Prompt, ProviderResponse

Effort = Literal["low", "medium", "high", "xhigh", "max"]
# 하네스 단계(prompting.STAGES)에서 image를 뺀 것. 이미지는 ImageProvider가 맡는다. 짝은 test_routing이 지킨다.
ROUTABLE_STAGES = ("diagnose", "easier_question", "propose_value", "generate", "generate_part", "validate")


def stage_targets(
    default_model: str,
    default_effort: str,
    stage_models: Mapping[str, str],
    stage_efforts: Mapping[str, str],
) -> dict[str, tuple[str, str]]:
    """[순수] 설정에 나온 단계마다 (모델, 노력). 정하지 않은 쪽은 기본값, 결과가 기본과 같으면 뺀다."""
    targets: dict[str, tuple[str, str]] = {}
    for stage in ROUTABLE_STAGES:
        if stage not in stage_models and stage not in stage_efforts:
            continue
        target = (stage_models.get(stage, default_model), stage_efforts.get(stage, default_effort))
        if target != (default_model, default_effort):
            targets[stage] = target
    return targets


class RoutedProvider:
    """단계 이름으로 제공자를 골라 그대로 넘긴다. 정하지 않은 단계는 기본 제공자."""

    def __init__(self, default: LLMProvider, routes: Mapping[str, LLMProvider]) -> None:
        self.default = default
        self.routes = dict(routes)
        self.name = default.name  # trace의 provider. 실제 모델 id는 응답의 model로 남는다

    def complete(
        self, *, task_type: str, stage: str, prompt: Prompt, response_model: type[BaseModel] | None = None
    ) -> ProviderResponse:
        provider = self.routes.get(stage, self.default)
        return provider.complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)
