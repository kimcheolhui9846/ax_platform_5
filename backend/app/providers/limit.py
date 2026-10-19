"""AI 동시 호출 상한. 실제 모델 호출은 오래 걸려 몰리면 스레드·메모리를 오래 잡으므로 자리 수로 묶는다.

LLM·이미지 제공자를 감싸 자리(CallSlots) 하나를 같이 쓴다. 자리를 정해진 시간 안에 못 얻으면 ProviderBusy다
(API 503). 하네스는 그대로다. 프로세스 하나를 전제로 한다(세션 잠금·SQLite와 같다).
설계: docs/superpowers/specs/2026-10-19-ai-call-limit-design.md
"""
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from pydantic import BaseModel

from app.providers.base import LLMProvider, Prompt, ProviderBusy, ProviderResponse
from app.providers.image import GeneratedImage, ImageProvider


class CallSlots:
    def __init__(self, size: int, wait_seconds: float) -> None:
        if size < 1:
            raise ValueError("동시 호출 자리는 하나 이상이어야 합니다.")
        self._semaphore = threading.BoundedSemaphore(size)
        self.wait_seconds = wait_seconds

    @contextmanager
    def hold(self) -> Iterator[None]:
        """자리를 얻어 블록을 돌고 돌려준다. wait_seconds 안에 못 얻으면 ProviderBusy."""
        if not self._semaphore.acquire(timeout=self.wait_seconds):
            raise ProviderBusy(f"동시 호출 자리를 {self.wait_seconds:g}초 안에 얻지 못했습니다.")
        try:
            yield
        finally:
            self._semaphore.release()


class LimitedProvider:
    """LLM 호출을 자리 안에서만 넘긴다."""

    def __init__(self, inner: LLMProvider, slots: CallSlots) -> None:
        self.inner = inner
        self.slots = slots
        self.name = inner.name

    def complete(
        self, *, task_type: str, stage: str, prompt: Prompt, response_model: type[BaseModel] | None = None
    ) -> ProviderResponse:
        with self.slots.hold():
            return self.inner.complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)


class LimitedImageProvider:
    """이미지 호출도 같은 자리를 쓴다."""

    def __init__(self, inner: ImageProvider, slots: CallSlots) -> None:
        self.inner = inner
        self.slots = slots
        self.name = inner.name

    def generate(self, *, task_type: str, prompt: Prompt) -> GeneratedImage:
        with self.slots.hold():
            return self.inner.generate(task_type=task_type, prompt=prompt)
