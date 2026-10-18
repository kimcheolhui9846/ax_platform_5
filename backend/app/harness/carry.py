"""다음 과제로 이어가기. 이전 결과 버전의 사실·보완 정보를 새 과제 필드로 옮길 값을 정한다(모두 순수 함수)."""
import re
from collections.abc import Mapping, Sequence, Set

from app.core.results import section_text
from app.core.state import CarriedContext, CarriedItem, InfoItem, InfoSource, ResultVersion, SessionState
from app.harness.policy import FieldPolicy, TaskPolicy

SUMMARY_LIMIT = 160


def carry_values(
    facts: Mapping[str, InfoItem],
    supplements: Mapping[str, InfoItem],
    fields: Sequence[FieldPolicy],
    carry_over: Mapping[str, str],
    private: Set[str],
) -> list[CarriedItem]:
    """[순수] 새 과제 필드마다 가져올 값. 후보는 같은 이름, 그다음 carry_over에서 그 필드를 가리키는 이전 이름(적은 순서).

    사실이 보완 정보보다 먼저다. 값이 없는 필드는 빠진다. 이전 과제의 정책 기본값(출처 default)은 가져오지 않는다.
    가져온 이전 이름이 private(이전 작업에서 비공개였던 이름)에 있으면 그 항목은 비공개로 표시한다.
    """
    chosen = {n: i.value for n, i in facts.items() if i.source is not InfoSource.DEFAULT}
    values = {**{n: i.value for n, i in supplements.items()}, **chosen}
    items: list[CarriedItem] = []
    for f in fields:
        candidates = [f.name, *(src for src, dst in carry_over.items() if dst == f.name)]
        found = next((name for name in candidates if values.get(name, "").strip()), None)
        if found is not None:
            items.append(CarriedItem(field=f.name, value=values[found].strip(), from_name=found, private=found in private))
    return items


def summarize(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """[순수] 공백을 하나로 줄이고 limit자를 넘으면 잘라 …을 붙인다."""
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def build_context(
    source: SessionState, version: ResultVersion, source_title: str, target: TaskPolicy, source_private: Set[str]
) -> CarriedContext:
    """[순수] 이전 세션의 그 버전으로 다음 과제에 가져올 기준(미리보기와 세션 만들기가 같이 쓴다).

    그 버전을 만들 때 비공개였거나 이전 세션에서 지금 비공개인(source_private) 이름은 가져와도 비공개다.
    """
    private = set(version.private or ()) | set(source_private)
    sections = sorted(version.result.sections, key=lambda s: s.order)
    return CarriedContext(
        session_id=source.session_id,
        task_type=source.task_type,
        version=version.version,
        title=f"{source_title} 초안 V{version.version}",
        summary=summarize(section_text(sections[0])) if sections else "",
        items=carry_values(version.facts, version.supplements, target.fields, target.carry_over, private),
    )
