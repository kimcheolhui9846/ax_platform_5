"""프롬프트에 들어가는 바깥 값(사용자 입력·이전 AI 출력) 다루기. 전부 순수 함수다.

바깥 값은 템플릿에서 inline·block 필터를 거쳐 <user_input> 태그 안에만 들어간다. 값 속 <·>는
바꿔 두므로 태그를 닫고 밖으로 나올 수 없고, 한 줄 값은 줄바꿈을 지워 틀(## 제목·- 줄)을 흉내 내지 못한다.
세션 값은 그대로이고 프롬프트만 바뀐다.
"""

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel

TAG_OPEN = "<user_input>"
TAG_CLOSE = "</user_input>"


def _escape(value: object) -> str:
    return str(value).replace("<", "&lt;").replace(">", "&gt;")


def inline(value: object) -> str:
    """[순수] 한 줄 값. 줄바꿈을 공백 하나로 바꾸고 태그로 감싼다."""
    flat = " ".join(_escape(value).replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    return f"{TAG_OPEN}{flat}{TAG_CLOSE}"


def block(value: object) -> str:
    """[순수] 여러 줄 글. 줄바꿈은 두고 태그 줄 사이에 넣는다."""
    return f"{TAG_OPEN}\n{_escape(value)}\n{TAG_CLOSE}"


LEAK_MIN_CHARS = 20  # 이보다 짧은 줄은 흔한 표현과 겹치므로 유출로 보지 않는다


def leaked_lines(system: str, texts: Iterable[str]) -> list[str]:
    """[순수] system 프롬프트의 줄 중 AI 출력에 그대로 들어간 것(앞의 -·#·공백을 뗀 글, LEAK_MIN_CHARS 이상)."""
    outputs = list(texts)
    found: list[str] = []
    for raw in system.splitlines():
        line = raw.lstrip("-# \t").strip()
        if len(line) >= LEAK_MIN_CHARS and line not in found and any(line in text for text in outputs):
            found.append(line)
    return found


def output_texts(model: BaseModel) -> list[str]:
    """[순수] 응답 모델의 모든 문자열 값(중첩 모델·목록·사전 포함)."""
    texts: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)

    walk(model.model_dump())
    return texts
