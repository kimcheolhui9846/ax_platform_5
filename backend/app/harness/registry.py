"""task_type → 과제 하네스. 새 과제는 tasks/ 아래 폴더를 만들고 TASK_TYPES에 추가한다."""
import importlib
from pathlib import Path

from app.core.assets import AssetStore
from app.harness.base import BaseHarness
from app.harness.errors import UnknownTaskError
from app.providers.base import LLMProvider
from app.providers.image import ImageProvider

TASKS_DIR = Path(__file__).parent / "tasks"
TASK_TYPES = ("business_plan", "product_planning", "branding", "marketing_content")


def harness_class(task_type: str) -> type[BaseHarness]:
    """과제의 하네스 클래스. 등록되지 않은 과제는 UnknownTaskError."""
    if task_type not in TASK_TYPES:
        raise UnknownTaskError(task_type)
    return importlib.import_module(f"app.harness.tasks.{task_type}.harness").Harness


def build_harness(
    task_type: str, provider: LLMProvider, images: ImageProvider | None = None, assets: AssetStore | None = None
) -> BaseHarness:
    return harness_class(task_type)(TASKS_DIR / task_type, provider, images, assets)


class HarnessRegistry:
    def __init__(self, provider: LLMProvider, images: ImageProvider | None = None, assets: AssetStore | None = None) -> None:
        self._harnesses = {t: build_harness(t, provider, images, assets) for t in TASK_TYPES}

    def __contains__(self, task_type: object) -> bool:
        return task_type in self._harnesses

    def get(self, task_type: str) -> BaseHarness:
        try:
            return self._harnesses[task_type]
        except KeyError:
            raise UnknownTaskError(task_type) from None

    def all(self) -> list[BaseHarness]:
        return list(self._harnesses.values())
