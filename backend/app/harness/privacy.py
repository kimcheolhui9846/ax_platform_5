"""외부 AI로 나가는 내용 거르기. 모두 순수 함수다.

세션 상태에는 원래 값이 남고, 프롬프트와 trace에만 거른 내용이 들어간다(설계서 2026-10-18-outbound-privacy-design).
"""
import re
from collections.abc import Iterable, Mapping
from typing import TypeVar

from app.core.state import InfoItem, SessionState
from app.providers.base import Prompt

_T = TypeVar("_T", bound=InfoItem)

# 외부 전송 안내 문구 버전. frontend/src/lib/privacy.ts의 NOTICE_TEXT를 바꾸면 이 값도 올린다(짝)
NOTICE_VERSION = "2026-10-18"

PRIVATE_MARK = "[비공개 입력 · AI에 보내지 않음]"

_BIRTH = r"(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"

# 겹치면 앞 줄이 먼저 바꾼다(주민번호·카드번호가 전화번호·계좌번호로 잘못 잡히지 않게)
_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    # 생년월일이 그럴듯해야 한다(월 01-12, 일 01-31). 바코드(EAN-13)가 걸리는 오탐은 놓치는 것보다 낫다고 보고 일부러 받아들인다
    ("resident", "[주민번호]", re.compile(
        r"(?<!\d)(?:\d{2}" + _BIRTH + r" ?- ?|\d{2}" + _BIRTH + r" ?)[1-8]\d{6}(?!\d)")),
    ("card", "[카드번호]", re.compile(r"(?<!\d)(?:\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}|[3-6]\d{15})(?!\d)")),
    # 국제식(+82)·괄호 지역번호·대표번호(15xx-xxxx 등)도 전화번호다. 뒤에 숫자가 더 붙으면 전화번호가 아니다
    ("phone", "[전화번호]", re.compile(
        r"(?<!\d)(?:\+82[-. ]?0?\d{1,2}[-. ]?\d{3,4}[-. ]?\d{4}"
        r"|\(0\d{1,2}\) ?\d{3,4}[-. ]?\d{4}"
        r"|1(?:544|566|577|588|599|600|644|661|666|670|688|833|899)-\d{4}"
        r"|(?:01[016789]|0\d{1,2})[-. ]?\d{3,4}[-. ]?\d{4})(?!\d|-\d)")),
    # 숫자가 모두 10자리 이상이고 마지막 묶음이 4자리 이상이어야 한다(날짜 2026-10-18·품번 12-34-56 제외)
    ("account", "[계좌번호]", re.compile(
        r"(?<!\d)(?=(?:\d-?){10,})\d{2,6}-\d{2,6}-(?:\d{4,8}|\d{2,8}-\d{1,6})(?!\d|-\d)")),
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


def _mask(items: Mapping[str, _T], private: frozenset[str]) -> dict[str, _T]:
    return {name: (item.model_copy(update={"value": PRIVATE_MARK}) if name in private else item) for name, item in items.items()}


def masked_state(state: SessionState, private: frozenset[str], raw_input_field: str | None) -> SessionState:
    """[순수] 비공개 이름의 사실·가정·보완 정보·가져온 값을 표시 글로 바꾼 복사본(프롬프트 렌더용).

    처음 입력 필드가 비공개면 요청 글(raw_input)도 가린다(프롬프트의 '처음 입력한 내용').
    """
    update: dict[str, object] = {
        "facts": _mask(state.facts, private),
        "assumptions": _mask(state.assumptions, private),
        "supplements": _mask(state.supplements, private),
    }
    if raw_input_field is not None and raw_input_field in private:
        update["raw_input"] = PRIVATE_MARK
    if state.context is not None:
        items = [i.model_copy(update={"value": PRIVATE_MARK}) if i.field in private else i for i in state.context.items]
        update["context"] = state.context.model_copy(update={"items": items})
    return state.model_copy(update=update)


def outbound_prompt(prompt: Prompt) -> tuple[Prompt, dict[str, int]]:
    """[순수] system·user 둘 다 개인정보를 가린다. 개수는 합친다."""
    system, a = redact(prompt.system)
    user, b = redact(prompt.user)
    return Prompt(system=system, user=user), {k: a.get(k, 0) + b.get(k, 0) for k in a.keys() | b.keys()}
