"""다음 과제로 이어가기. 이전 결과 버전의 사실·보완 정보를 새 과제 필드로 옮길 값을 정한다(모두 순수 함수)."""
import re
from collections.abc import Mapping, Sequence

from app.core.results import section_text
from app.core.state import CarriedContext, CarriedItem, InfoItem, ResultVersion, SessionState
from app.harness.policy import FieldPolicy, TaskPolicy

SUMMARY_LIMIT = 160


def carry_values(
    facts: Mapping[str, InfoItem],
    supplements: Mapping[str, InfoItem],
    fields: Sequence[FieldPolicy],
    carry_over: Mapping[str, str],
) -> list[CarriedItem]:
    """[순수] 새 과제 필드마다 가져올 값. 후보는 같은 이름, 그다음 carry_over에서 그 필드를 가리키는 이전 이름(적은 순서).

    사실이 보완 정보보다 먼저다. 값이 없는 필드는 빠진다.
    """
    values = {**{n: i.value for n, i in supplements.items()}, **{n: i.value for n, i in facts.items()}}
    items: list[CarriedItem] = []
    for f in fields:
        candidates = [f.name, *(src for src, dst in carry_over.items() if dst == f.name)]
        found = next((name for name in candidates if values.get(name, "").strip()), None)
        if found is not None:
            items.append(CarriedItem(field=f.name, value=values[found].strip(), from_name=found))
    return items


def summarize(text: str, limit: int = SUMMARY_LIMIT) -> str:
    """[순수] 공백을 하나로 줄이고 limit자를 넘으면 잘라 …을 붙인다."""
    flat = re.sub(r"\s+", " ", text).strip()
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def build_context(source: SessionState, version: ResultVersion, source_title: str, target: TaskPolicy) -> CarriedContext:
    """[순수] 이전 세션의 그 버전으로 다음 과제에 가져올 기준(미리보기와 세션 만들기가 같이 쓴다)."""
    sections = sorted(version.result.sections, key=lambda s: s.order)
    return CarriedContext(
        session_id=source.session_id,
        task_type=source.task_type,
        version=version.version,
        title=f"{source_title} 초안 V{version.version}",
        summary=summarize(section_text(sections[0])) if sections else "",
        items=carry_values(version.facts, version.supplements, target.fields, target.carry_over),
    )
