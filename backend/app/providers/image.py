"""이미지 제공자 인터페이스와 비용 0의 Mock. 하네스의 image 단계만 쓴다.

실제 어댑터는 SDK 오류를 ProviderError로 감싸고, 이미지 형식(mime)은 app/core/assets.py의 IMAGE_MIMES 안에서 돌려준다.
"""
from dataclasses import dataclass
from typing import Protocol

from app.providers.base import Prompt, ProviderError


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    mime: str
    model: str  # 실제로 그린 모델 id


class ImageProvider(Protocol):
    name: str

    def generate(self, *, task_type: str, prompt: Prompt) -> GeneratedImage: ...


# 자리표시 이미지: 글자 대신 도형만 둔다(프롬프트 글을 넣지 않아 이스케이프할 것이 없다)
PLACEHOLDER_SVG = (
    b'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
    b'<rect width="640" height="360" fill="#f4f1ee"/>'
    b'<circle cx="250" cy="170" r="56" fill="#e3d6cf"/>'
    b'<rect x="330" y="120" width="120" height="100" rx="12" fill="#d6c3b8"/>'
    b'<rect x="190" y="250" width="260" height="14" rx="7" fill="#e3d6cf"/>'
    b"</svg>"
)


class MockImageProvider:
    name = "mock"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail  # 테스트용: 항상 실패
        self.calls: list[str] = []

    def generate(self, *, task_type: str, prompt: Prompt) -> GeneratedImage:
        self.calls.append(task_type)
        if self.fail:
            raise ProviderError("[mock] image 단계 호출 실패")
        return GeneratedImage(data=PLACEHOLDER_SVG, mime="image/svg+xml", model="mock-image")


def get_image_provider(name: str) -> ImageProvider:
    if name == "mock":
        return MockImageProvider()
    raise ValueError(f"지원하지 않는 image provider입니다: {name} (현재 지원: mock)")
