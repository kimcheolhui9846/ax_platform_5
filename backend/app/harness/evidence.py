"""근거 자료. 지금은 과제 폴더 evidence.yaml(샘플)을 읽는다. 실제 웹 검색을 붙이면 find_evidence만 바꾼다.

모르는 키(오타)는 읽을 때 거부한다. 원문 주소는 http(s)만 받는다(문서·화면 링크로 그대로 쓰이므로).
"""
from collections.abc import Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.results import CardType, EvidenceRecord, ResultSection, section_order_for


class EvidenceProposal(BaseModel):
    """결과에 붙일 점검 문구. 배경 자료에는 없다."""

    model_config = ConfigDict(extra="forbid")

    title: str
    text: str
    note: str = ""  # 출처 옆 한 줄(예: 제품 시험 전)
    caution: str = ""  # 반영하기 전에 보여 줄 안내


class EvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    title: str
    publisher: str
    meta: str
    summary: str
    scope: str  # 적용 범위(이 결과의 검증이 아님을 밝힌다)
    url: str = Field(pattern=r"^https?://")
    applies_to: CardType  # 기록을 둘 섹션 종류
    record: EvidenceProposal | None = None


class _Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[EvidenceSource]

    @model_validator(mode="after")
    def _unique_ids(self) -> "_Catalog":
        ids = [s.id for s in self.sources]
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        if repeated:
            raise ValueError(f"근거 자료 id가 중복됩니다: {', '.join(repeated)}")
        return self


def load_evidence(path: Path) -> list[EvidenceSource]:
    """과제의 샘플 근거 자료. 파일이 없으면 자료가 없는 과제다."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fp:
        return _Catalog.model_validate(yaml.safe_load(fp)).sources


def evidence_record(source: EvidenceSource, sections: Sequence[ResultSection]) -> EvidenceRecord:
    """[순수] 자료의 점검 문구를 결과에 붙일 기록으로. 점검 문구가 없는 자료는 부르는 쪽이 거른다."""
    if source.record is None:
        raise ValueError(f"점검 문구가 없는 자료입니다: {source.id}")
    return EvidenceRecord(
        source_id=source.id,
        title=source.record.title,
        text=source.record.text,
        note=source.record.note,
        source_title=source.title,
        publisher=source.publisher,
        url=source.url,
        section_kind=source.applies_to,
        section_order=section_order_for(sections, source.applies_to),
    )
