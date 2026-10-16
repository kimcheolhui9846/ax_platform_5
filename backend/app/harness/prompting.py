"""프롬프트 템플릿 렌더링. 과제 폴더 prompts/가 공통 harness/prompts/보다 우선한다.

단계마다 템플릿에 넘기는 변수를 STAGE_CONTEXT에 한 번만 적는다. 렌더링할 때 넘긴 키가
선언과 다르면 바로 실패하므로, 템플릿이 다른 단계의 변수를 쓰면 테스트에서 드러난다.
"""
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined

from app.core.state import source_label

COMMON_PROMPTS_DIR = Path(__file__).parent / "prompts"

COMMON_CONTEXT = frozenset({"state", "policy", "profile"})  # 모든 단계 공통
STAGE_CONTEXT: dict[str, frozenset[str]] = {
    "diagnose": frozenset(),
    "easier_question": frozenset({"field", "level", "previous"}),
    "propose_value": frozenset({"field", "level", "previous"}),
    "generate": frozenset({"output_schema"}),
    "validate": frozenset({"result_text"}),
}
STAGES = tuple(STAGE_CONTEXT)


class PromptContextError(ValueError):
    """단계에 넘긴 템플릿 변수가 STAGE_CONTEXT 선언과 다르다(코드 오류)."""


def context_keys(stage: str) -> frozenset[str]:
    """[순수] 이 단계 템플릿이 받는 변수 이름 전부."""
    if stage not in STAGE_CONTEXT:
        raise PromptContextError(f"없는 단계입니다: {stage}")
    return COMMON_CONTEXT | STAGE_CONTEXT[stage]


def check_context(stage: str, keys: set[str]) -> None:
    """[순수] 넘긴 키가 단계 선언과 정확히 같지 않으면 PromptContextError."""
    expected = context_keys(stage)
    missing = sorted(expected - keys)
    unexpected = sorted(keys - expected)
    if missing or unexpected:
        raise PromptContextError(
            f"{stage} 단계 템플릿 변수가 선언과 다릅니다. "
            f"빠짐: {', '.join(missing) or '없음'} / 선언 밖: {', '.join(unexpected) or '없음'}"
        )


class PromptRenderer:
    def __init__(self, task_prompts_dir: Path) -> None:
        self.env = Environment(
            loader=ChoiceLoader(
                [FileSystemLoader(task_prompts_dir), FileSystemLoader(COMMON_PROMPTS_DIR)]
            ),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,  # {% %} 태그 줄이 빈 줄을 남기지 않는다
            lstrip_blocks=True,
            autoescape=False,
        )
        self.env.filters["source_label"] = source_label

    def render(self, stage: str, **context: Any) -> str:
        check_context(stage, set(context))
        return self.env.get_template(f"{stage}.md").render(**context)
