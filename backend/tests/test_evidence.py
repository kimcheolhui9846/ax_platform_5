"""근거 자료(샘플): evidence.yaml을 find_evidence가 내고, 반영은 직전 기준을 이어받은 evidence 버전이다."""
import pytest

from app.core.messages import EVIDENCE_NO_RECORD_MESSAGE, EVIDENCE_NOT_FOUND_MESSAGE, RESULT_NOT_READY_MESSAGE
from app.core.results import CardType, EvidenceRecord, ResultSection, TextBlock, VersionReason, carry_evidence, section_order_for
from app.core.state import Answer, AnswerType
from app.harness.errors import HarnessError
from app.harness.evidence import EvidenceSource, load_evidence
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import OTHER_CLIENT_ID, api_client

BASE = "/api/v1/coaching"


def section(order: int, kind: CardType) -> ResultSection:
    return ResultSection(order=order, heading=f"h{order}", kind=kind, blocks=[TextBlock(text="t")])


def record(kind: CardType, order: int | None) -> EvidenceRecord:
    return EvidenceRecord(
        source_id="s1", title="점검", text="점검 문구", note="", source_title="자료", publisher="기관",
        url="https://example.com", section_kind=kind, section_order=order,
    )


def test_section_order_for_picks_the_first_section_of_that_kind():
    sections = [section(1, CardType.DIAGNOSIS), section(2, CardType.SUGGESTION), section(3, CardType.SUGGESTION)]
    assert section_order_for(sections, CardType.SUGGESTION) == 2
    assert section_order_for(sections, CardType.ACTION) is None


def test_carry_evidence_places_records_again_in_new_sections():
    carried = carry_evidence([record(CardType.ACTION, 4)], [section(1, CardType.DIAGNOSIS), section(2, CardType.ACTION)])
    assert [r.section_order for r in carried] == [2]
    assert carry_evidence([record(CardType.ACTION, 2)], [section(1, CardType.DIAGNOSIS)])[0].section_order is None


def test_evidence_yaml_rejects_unknown_keys_and_unsafe_urls(tmp_path):
    path = tmp_path / "evidence.yaml"
    path.write_text("sources:\n  - {id: a, title: t, publisher: p, meta: m, summary: s, scope: c, url: 'javascript:alert(1)', applies_to: action}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_evidence(path)
    path.write_text("sources:\n  - {id: a, title: t, publisher: p, meta: m, summary: s, scope: c, url: 'https://x', applies_to: action, typo: 1}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_evidence(path)
    assert load_evidence(tmp_path / "none.yaml") == []  # 자료가 없는 과제


def test_find_evidence_returns_the_sample_sources(harness):
    sources = harness.find_evidence(harness.start("향초"))
    assert [s.id for s in sources] == ["zipper_caution", "craft_fair"]
    assert isinstance(sources[0], EvidenceSource)


def test_apply_evidence_adds_a_version_with_the_record_and_previous_basis(harness, provider, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    first_question = state.asked_questions[0].question.question_id
    harness.revise_answer(state, Answer(question_id=first_question, answer_type=AnswerType.FREE_TEXT, value="초등학생 부모"))
    calls = len(provider.calls)

    assert harness.apply_evidence(state, "zipper_caution") is True

    latest = state.versions[-1]
    assert (latest.version, latest.reason) == (2, VersionReason.EVIDENCE)
    [applied] = state.result.evidence
    assert (applied.source_id, applied.title, applied.note, applied.url) == (
        "zipper_caution", "제작 점검 항목", "제품 시험 전", "https://example.com/zipper"
    )
    assert applied.section_order == section_order_for(state.result.sections, CardType.SUGGESTION)
    assert latest.facts["customer"].value == "부모"  # 직전 버전의 기준을 이어받는다
    assert state.result_stale is True  # 답이 바뀐 것은 그대로다
    assert len(provider.calls) == calls  # LLM을 부르지 않는다


def test_applying_the_same_source_again_adds_no_version(harness):
    state = harness.start("향초")
    harness.generate(state)
    harness.apply_evidence(state, "zipper_caution")

    assert harness.apply_evidence(state, "zipper_caution") is True
    assert len(state.versions) == 2


def test_apply_evidence_rejects_background_sources_and_unknown_ids(harness):
    state = harness.start("향초")
    harness.generate(state)
    with pytest.raises(HarnessError, match=EVIDENCE_NO_RECORD_MESSAGE):
        harness.apply_evidence(state, "craft_fair")
    assert harness.apply_evidence(state, "nope") is False
    assert len(state.versions) == 1


def test_regenerating_keeps_applied_evidence_in_the_new_draft(harness, reply):
    state = harness.start("향초")
    harness.generate(state)
    harness.apply_evidence(state, "zipper_caution")

    harness.generate(state)

    assert state.versions[-1].reason is VersionReason.REGENERATE
    assert [r.source_id for r in state.result.evidence] == ["zipper_caution"]


def test_editing_text_keeps_the_evidence_record(harness):
    state = harness.start("향초")
    harness.generate(state)
    harness.apply_evidence(state, "zipper_caution")

    harness.edit_section(state, state.result.sections[0].order, "고친 글")

    assert [r.source_id for r in state.result.evidence] == ["zipper_caution"]


def test_evidence_api():
    client = api_client(create_app(provider=MockProvider(), debug=True))
    tasks = {t["task_type"]: t["evidence_sources"] for t in client.get(f"{BASE}/tasks").json()}
    assert tasks == {"business_plan": 0, "product_planning": 2, "branding": 0, "marketing_content": 0}
    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "한글 파우치"}).json()["session_id"]

    before = client.get(f"{BASE}/sessions/{sid}/evidence")
    assert (before.status_code, before.json()) == (404, {"detail": RESULT_NOT_READY_MESSAGE})

    client.post(f"{BASE}/sessions/{sid}/generate")
    items = client.get(f"{BASE}/sessions/{sid}/evidence").json()
    assert [i["id"] for i in items] == ["ykk_zipper_caution", "kcdf_craft_trend_fair_2025"]
    assert items[0]["record"]["title"] == "제작 점검 항목"
    assert set(items[0]["record"]) == {"title", "text", "note", "caution"}
    assert items[0]["record"]["note"] and items[0]["record"]["caution"]
    assert items[0]["applies_to"] == "suggestion"
    assert items[1]["record"] is None

    applied = client.post(f"{BASE}/sessions/{sid}/evidence/ykk_zipper_caution/apply")
    assert applied.status_code == 200
    body = applied.json()
    assert body["version"]["reason"] == "evidence"
    assert [r["source_id"] for r in body["result"]["evidence"]] == ["ykk_zipper_caution"]

    assert client.post(f"{BASE}/sessions/{sid}/evidence/nope/apply").json() == {"detail": EVIDENCE_NOT_FOUND_MESSAGE}
    background = client.post(f"{BASE}/sessions/{sid}/evidence/kcdf_craft_trend_fair_2025/apply")
    assert (background.status_code, background.json()) == (422, {"detail": EVIDENCE_NO_RECORD_MESSAGE})
    assert api_client(client.app, client_id=OTHER_CLIENT_ID).get(f"{BASE}/sessions/{sid}/evidence").status_code == 404


def test_apply_evidence_api_without_a_result_is_404_result_not_ready():
    client = api_client(create_app(provider=MockProvider(), debug=True))
    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "한글 파우치"}).json()["session_id"]

    response = client.post(f"{BASE}/sessions/{sid}/evidence/ykk_zipper_caution/apply")

    assert (response.status_code, response.json()) == (404, {"detail": RESULT_NOT_READY_MESSAGE})
