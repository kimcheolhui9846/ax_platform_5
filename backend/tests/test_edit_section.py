"""결과 문구 수정: 섹션 하나의 글을 바꾼 새 버전(edit). LLM을 부르지 않고 기준·최신 여부는 그대로다."""
import pytest

from app.core.messages import RESULT_NOT_READY_MESSAGE, SECTION_NOT_FOUND_MESSAGE
from app.core.results import VersionReason, section_text, with_section_text
from app.core.state import Answer, AnswerType
from app.harness.errors import HarnessError
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


def test_with_section_text_replaces_one_section_and_rebuilds_full_text(harness):
    state = harness.start("향초")
    harness.generate(state)
    first = state.result.sections[0]

    edited = with_section_text(state.result, first.order, "한글 형태를 담은 작은 정리 파우치")

    assert section_text(edited.sections[0]) == "한글 형태를 담은 작은 정리 파우치"
    assert edited.full_text.startswith(f"{first.heading}\n한글 형태를 담은 작은 정리 파우치")
    assert section_text(state.result.sections[0]) != "한글 형태를 담은 작은 정리 파우치"  # 원본은 그대로
    assert with_section_text(state.result, 99, "x") is None


def test_edit_adds_a_version_with_the_previous_basis_and_no_llm_call(harness, provider, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    first_question = state.asked_questions[0].question.question_id

    harness.revise_answer(state, Answer(question_id=first_question, answer_type=AnswerType.FREE_TEXT, value="초등학생 부모"))
    assert state.result_stale is True
    calls = len(provider.calls)

    assert harness.edit_section(state, state.result.sections[0].order, "  고친 문구  ") is True

    assert [(v.version, v.reason) for v in state.versions][-1] == (2, VersionReason.EDIT)
    assert section_text(state.result.sections[0]) == "고친 문구"
    assert state.versions[-1].result == state.result
    assert state.versions[-1].facts["customer"].value == "부모"  # 직전 버전의 기준을 이어받는다
    assert state.result_stale is True  # 답이 바뀐 것은 그대로다
    assert len(provider.calls) == calls


def test_edit_rejects_empty_text_and_unknown_sections(harness):
    state = harness.start("향초")
    harness.generate(state)
    before = state.model_dump(exclude={"trace"})

    with pytest.raises(HarnessError, match="고칠 문구가 비어 있습니다."):
        harness.edit_section(state, state.result.sections[0].order, "   ")
    assert harness.edit_section(state, 99, "x") is False
    assert state.model_dump(exclude={"trace"}) == before


def test_edit_api():
    client = api_client(create_app(provider=MockProvider(), debug=True))
    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}).json()["session_id"]
    assert client.patch(f"{BASE}/sessions/{sid}/result/sections/1", json={"text": "x"}).json() == {
        "detail": RESULT_NOT_READY_MESSAGE
    }
    order = client.post(f"{BASE}/sessions/{sid}/generate").json()["result"]["sections"][0]["order"]

    edited = client.patch(f"{BASE}/sessions/{sid}/result/sections/{order}", json={"text": "고친 문구"})

    assert edited.status_code == 200
    body = edited.json()
    assert (body["version"]["version"], body["version"]["reason"]) == (2, "edit")
    assert body["result"]["sections"][0]["blocks"] == [{"type": "text", "text": "고친 문구"}]
    missing = client.patch(f"{BASE}/sessions/{sid}/result/sections/99", json={"text": "x"})
    assert (missing.status_code, missing.json()) == (404, {"detail": SECTION_NOT_FOUND_MESSAGE})
    assert client.patch(f"{BASE}/sessions/{sid}/result/sections/{order}", json={"text": ""}).status_code == 422


def test_edit_validates_against_the_previous_versions_basis(harness, reply):
    seen = []

    def spy(state, result, policy):
        seen.append(dict(state.facts))
        return []

    harness.validators = [spy]
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    old_facts = {k: v.value for k, v in state.versions[-1].facts.items()}
    first_question = state.asked_questions[0].question.question_id
    harness.revise_answer(state, Answer(question_id=first_question, answer_type=AnswerType.FREE_TEXT, value="초등학생 부모"))
    assert {k: v.value for k, v in state.facts.items()} != old_facts
    seen.clear()

    assert harness.edit_section(state, state.result.sections[0].order, "고친 문구") is True

    assert {k: v.value for k, v in seen[-1].items()} == old_facts


def test_editing_to_the_same_text_makes_no_version(harness):
    state = harness.start("향초")
    harness.generate(state)
    section = state.result.sections[0]
    before = state.model_dump(exclude={"trace"})

    assert harness.edit_section(state, section.order, f"  {section_text(section)} ") is True

    assert state.model_dump(exclude={"trace"}) == before
    assert len(state.versions) == 1
