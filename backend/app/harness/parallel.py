"""병렬 생성의 순수 부분: 조각 스키마 만들기, 스키마와 맞는지 확인, 합치기, 캐시 키.

결과 항목(과제 output_schema 필드)을 정책 parallel_generation의 조각으로 나눠 동시에 부르고(BaseHarness.generate),
여기서 코드로 합친다(LLM 없음). 기본 꺼짐이고 측정 뒤 켠다(docs/HARNESS-ROADMAP.md 0단계).
설계: docs/superpowers/specs/2026-10-19-parallel-generation-design.md
"""
import hashlib
from collections.abc import Sequence
from typing import Generic

from pydantic import BaseModel, Field, create_model

from app.core.results import (
    ContentT,
    GenerationResult,
    ResultAssumption,
    ResultCard,
    compose_full_text,
    sections_from_cards,
)
from app.harness.policy import ParallelGeneration
from app.providers.base import Prompt


class PartResult(BaseModel, Generic[ContentT]):
    """조각 하나가 채우는 형태. 완성본(full_text)은 받지 않고 합친 섹션으로 만든다."""

    cards: list[ResultCard] = Field(description="이 조각이 다루는 결과 항목의 모바일 결과 카드")
    assumptions: list[ResultAssumption] = Field(default_factory=list, description="AI가 가정으로 보완한 항목")
    content: ContentT


def check_parts(parallel: ParallelGeneration, content_model: type[BaseModel]) -> None:
    """[순수] 조각들이 결과 스키마 필드를 빠짐없이 덮는지. 모자라거나 모르는 이름이면 ValueError."""
    covered = {f for part in parallel.parts for f in part.content}
    fields = set(content_model.model_fields)
    missing, unknown = sorted(fields - covered), sorted(covered - fields)
    if missing or unknown:
        raise ValueError(
            f"parallel_generation 조각이 {content_model.__name__}와 맞지 않습니다. "
            f"빠짐: {', '.join(missing) or '없음'} / 모르는 이름: {', '.join(unknown) or '없음'}"
        )


def part_models(parallel: ParallelGeneration, content_model: type[BaseModel]) -> dict[str, type[PartResult]]:
    """[순수] 조각 이름 → 그 조각 필드만 가진 응답 모델."""
    models: dict[str, type[PartResult]] = {}
    for part in parallel.parts:
        fields = {name: (content_model.model_fields[name].annotation, content_model.model_fields[name]) for name in part.content}
        name = f"{content_model.__name__}_{part.name}"
        models[part.name] = PartResult[create_model(name, **fields)]  # type: ignore[call-overload, misc]
    return models


def merge_parts(parts: Sequence[PartResult], content_model: type[BaseModel]) -> GenerationResult:
    """[순수] 조각 순서대로 합친다. content는 전체 스키마로 검증, 카드는 조각 순서대로 번호를 다시 매기고,
    가정은 같은 필드면 처음 것만 남긴다. 완성본은 섹션으로 다시 만든다."""
    content: dict = {}
    cards: list[ResultCard] = []
    assumptions: list[ResultAssumption] = []
    seen: set[str] = set()
    for part in parts:
        content |= part.content.model_dump(mode="json")
        for c in sorted(part.cards, key=lambda c: c.order):  # 안정 정렬: 같은 order는 쓴 순서
            cards.append(c.model_copy(update={"order": len(cards) + 1}))
        for a in part.assumptions:
            if a.field not in seen:
                seen.add(a.field)
                assumptions.append(a)
    sections = sections_from_cards(cards)
    return GenerationResult(
        sections=sections,
        assumptions=assumptions,
        full_text=compose_full_text(sections),
        content=content_model.model_validate(content).model_dump(mode="json"),
    )


def prompt_key(prompt: Prompt) -> str:
    """[순수] 나갈 프롬프트의 해시. 입력·비공개 설정·정책이 바뀌면 달라진다."""
    return hashlib.sha256(f"{prompt.system}\0{prompt.user}".encode()).hexdigest()
