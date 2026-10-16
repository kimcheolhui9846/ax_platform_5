"""task_type → 과제 하네스. 새 과제는 tasks/ 아래 폴더를 만들고 TASK_TYPES에 추가한다."""
import importlib
from pathlib import Path

from app.harness.base import BaseHarness
from app.harness.errors import UnknownTaskError
from app.providers.base import LLMProvider

TASKS_DIR = Path(__file__).parent / "tasks"
TASK_TYPES = ("business_plan", "product_planning", "branding", "marketing_content")


def build_harness(task_type: str, provider: LLMProvider) -> BaseHarness:
    module = importlib.import_module(f"app.harness.tasks.{task_type}.harness")
    return module.Harness(TASKS_DIR / task_type, provider)


class HarnessRegistry:
    def __init__(self, provider: LLMProvider) -> None:
        self._harnesses = {t: build_harness(t, provider) for t in TASK_TYPES}

    def get(self, task_type: str) -> BaseHarness:
        try:
            return self._harnesses[task_type]
        except KeyError:
            raise UnknownTaskError(task_type) from None

    def all(self) -> list[BaseHarness]:
        return list(self._harnesses.values())
