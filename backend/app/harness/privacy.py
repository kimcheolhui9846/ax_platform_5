"""외부 AI로 나가는 내용 거르기. 모두 순수 함수다.

세션 상태에는 원래 값이 남고, 프롬프트와 trace에만 거른 내용이 들어간다(설계서 2026-10-18-outbound-privacy-design).
"""
import re
from collections.abc import Iterable, Mapping

from app.core.state import SessionState
from app.providers.base import Prompt

PRIVATE_MARK = "[비공개 입력 · AI에 보내지 않음]"

# 겹치면 앞 줄이 먼저 바꾼다(주민번호·카드번호가 전화번호·계좌번호로 잘못 잡히지 않게)
_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("resident", "[주민번호]", re.compile(r"(?<!\d)\d{6}-?[1-8]\d{6}(?!\d)")),
    ("card", "[카드번호]", re.compile(r"(?<!\d)\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}(?!\d)")),
    ("phone", "[전화번호]", re.compile(r"(?<!\d)(?:01[016789]|0\d{1,2})[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    ("account", "[계좌번호]", re.compile(r"(?<!\d)\d{2,6}-\d{2,6}-\d{2,6}(?:-\d{1,6})?(?!\d)")),
    ("email", "[이메일]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """[순수] 개인정보 패턴을 표시 글로 바꾸고 종류별 개수를 돌려준다. 되돌리지 않는다."""
    counts: dict[str, int] = {}
    for kind, mark, pattern in _PATTERNS:
        text, n = pattern.subn(mark, text)
        if n:
            counts[kind] = counts.get(kind, 0) + n
    return text, counts


def private_names(defaults: Iterable[str], overrides: Mapping[str, bool]) -> frozenset[str]:
    """[순수] 비공개 이름: 정책 기본값에 사용자 설정(True 더함, False 뺌)을 덮은 것."""
    names = set(defaults)
    for name, private in overrides.items():
        (names.add if private else names.discard)(name)
    return frozenset(names)


def _mask(items, private):
    return {name: (item.model_copy(update={"value": PRIVATE_MARK}) if name in private else item) for name, item in items.items()}


def masked_state(state: SessionState, private: frozenset[str]) -> SessionState:
    """[순수] 비공개 이름의 사실·가정·보완 정보·가져온 값을 표시 글로 바꾼 복사본(프롬프트 렌더용)."""
    update = {
        "facts": _mask(state.facts, private),
        "assumptions": _mask(state.assumptions, private),
        "supplements": _mask(state.supplements, private),
    }
    if state.context is not None:
        items = [i.model_copy(update={"value": PRIVATE_MARK}) if i.field in private else i for i in state.context.items]
        update["context"] = state.context.model_copy(update={"items": items})
    return state.model_copy(update=update)


def outbound_prompt(prompt: Prompt) -> tuple[Prompt, dict[str, int]]:
    """[순수] system·user 둘 다 개인정보를 가린다. 개수는 합친다."""
    system, a = redact(prompt.system)
    user, b = redact(prompt.user)
    return Prompt(system=system, user=user), {k: a.get(k, 0) + b.get(k, 0) for k in a.keys() | b.keys()}
