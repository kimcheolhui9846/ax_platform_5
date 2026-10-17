"""미확인 정보 보완: 사용자 입력(검증 전)으로 두었다가 다음 생성에 반영한다(supplement 버전)."""
import pytest

from app.core.results import VersionReason
from app.core.state import Answer, AnswerType, InfoItem, InfoSource
from app.harness.base import apply_supplements, generate_reason, supplements_changed
from app.harness.errors import HarnessError
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


def item(value: str) -> InfoItem:
    return InfoItem(value=value, source=InfoSource.USER_SUPPLEMENT)


def test_apply_supplements_sets_trims_and_clears():
    current = {"material": item("면"), "size": item("작음")}

    merged = apply_supplements(current, {"material": "  리넨 ", "size": None, "price": "18,000원", "budget": "  "})

    assert {k: v.value for k, v in merged.items()} == {"material": "리넨", "price": "18,000원"}
    assert all(v.source is InfoSource.USER_SUPPLEMENT for v in merged.values())
    assert {k: v.value for k, v in current.items()} == {"material": "면", "size": "작음"}  # 원본은 그대로


def test_set_supplements_marks_the_result_stale_and_rejects_unknown_names(harness):
    state = harness.start("향초")
    harness.generate(state)

    harness.set_supplements(state, {"material": "면 100%"})

    assert state.supplements["material"].value == "면 100%"
    assert state.supplements["material"].source is InfoSource.USER_SUPPLEMENT
    assert state.result_stale is True
    assert state.status.value == "revising"  # 생성 뒤 걸린 질문이 없으니 '다시 만들 때'다
    with pytest.raises(HarnessError, match="보완할 수 없는 항목입니다: nope"):
        harness.set_supplements(state, {"nope": "x"})


def test_same_values_change_nothing(harness):
    state = harness.start("향초")
    harness.set_supplements(state, {"material": "면"})
    harness.generate(state)

    harness.set_supplements(state, {"material": "면"})

    assert state.result_stale is False


def test_generate_after_only_supplements_changed_is_a_supplement_version(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))
    harness.generate(state)
    assert generate_reason(state) is VersionReason.REGENERATE
    harness.set_supplements(state, {"material": "면"})
    assert supplements_changed(state.supplements, state.versions[-1]) is True

    harness.generate(state)

    latest = state.versions[-1]
    assert (latest.version, latest.reason) == (2, VersionReason.SUPPLEMENT)
    assert latest.supplements["material"].value == "면"
    assert supplements_changed(state.supplements, latest) is False

    first_question = state.asked_questions[0].question.question_id  # 답이 바뀌면 다시 만든 초안이다
    harness.revise_answer(state, Answer(question_id=first_question, answer_type=AnswerType.FREE_TEXT, value="초등학생 부모"))
    harness.set_supplements(state, {"material": "리넨"})
    assert generate_reason(state) is VersionReason.REGENERATE


def test_supplements_reach_the_generate_prompt(harness):
    state = harness.start("향초")
    harness.set_supplements(state, {"material": "면 100%"})

    harness.generate(state)

    prompt = next(t for t in reversed(state.trace) if t.stage == "generate").input["user"]
    assert "## 보완 정보 (사용자 입력 · 검증 전)" in prompt
    assert "- material (소재): 면 100%" in prompt


def test_supplements_api():
    client = api_client(create_app(provider=MockProvider(), debug=True))
    view = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초"}).json()
    sid = view["session_id"]
    assert [s["name"] for s in view["supplements"]][:2] == ["target_customer", "material"]
    assert view["supplements"][1] == {"name": "material", "label": "소재", "example": "면 100%", "value": None}
    assert view["supplements_changed"] is False

    saved = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"material": "면 100%"}})
    assert saved.status_code == 200
    assert saved.json()["supplements"][1]["value"] == "면 100%"
    assert saved.json()["supplements_changed"] is True

    result = client.post(f"{BASE}/sessions/{sid}/generate").json()
    assert result["version"]["reason"] == "first"
    assert next(s for s in result["supplements"] if s["name"] == "material")["value"] == "면 100%"
    assert client.get(f"{BASE}/sessions/{sid}").json()["supplements_changed"] is False

    bad = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"nope": "x"}})
    assert bad.status_code == 422
    too_long = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"material": "x" * 251}})
    assert too_long.status_code == 422
