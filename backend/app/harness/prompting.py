"""프롬프트 템플릿 렌더링. 과제 폴더 prompts/가 공통 harness/prompts/보다 우선한다."""
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined

COMMON_PROMPTS_DIR = Path(__file__).parent / "prompts"
STAGES = ("diagnose", "easier_question", "propose_value", "generate", "validate")


class PromptRenderer:
    def __init__(self, task_prompts_dir: Path) -> None:
        self.env = Environment(
            loader=ChoiceLoader(
                [FileSystemLoader(task_prompts_dir), FileSystemLoader(COMMON_PROMPTS_DIR)]
            ),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,
        )

    def render(self, stage: str, **context: Any) -> str:
        return self.env.get_template(f"{stage}.md").render(**context)
