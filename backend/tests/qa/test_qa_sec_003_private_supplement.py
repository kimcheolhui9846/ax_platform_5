"""TC-SEC-003: 정보 입력·수정(보완 정보)에서 'AI에 보내지 않기'를 체크하면 그 값이 AI 요청에서 빠진다.

IR 피치덱의 희망 투자 금액(funding_amount)과 사업계획의 예산(budget)을 체크·해제 두 경우로 확인한다.
두 항목은 정책상 기본 비공개라 '해제'는 private False를 명시해 저장한다.
"""
import pytest

from app.harness.privacy import PRIVATE_MARK
from tests.acceptance.flow import BASE, answer_all, generate, start

VALUE = "7777만원"
CASES = [("ir_pitch", "funding_amount"), ("business_plan", "budget")]


def _draft_then_save_supplement(client, recorder, task: str, name: str, private: bool) -> dict:
    """초안을 만든 뒤 보완 정보를 저장하고 다시 만든다. 다시 만든 생성 요청의 프롬프트만 따로 본다."""
    view, _ = answer_all(client, start(client, task))
    sid = view["session_id"]
    generate(client, sid)
    saved = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {name: VALUE}, "private": {name: private}})
    assert saved.status_code == 200, saved.text
    item = next(s for s in saved.json()["supplements"] if s["name"] == name)
    assert (item["value"], item["private"]) == (VALUE, private)
    before = len(recorder.prompts)
    result = generate(client, sid)  # 초안에 반영(다시 만들기)
    return {"result": result, "new_prompts": recorder.prompts[before:]}


def _sent(prompts) -> str:
    return "\n".join(p.system + "\n" + p.user for _, p in prompts)


@pytest.mark.parametrize(("task", "name"), CASES)
def test_qa_sec_003_checked_supplement_is_not_sent_to_ai(client, recorder, task, name):
    run = _draft_then_save_supplement(client, recorder, task, name, private=True)
    assert "generate" in [s for s, _ in run["new_prompts"]]
    assert VALUE not in recorder.outbound_text()  # 세션 전체의 어떤 AI 요청에도 없다
    assert PRIVATE_MARK in _sent(run["new_prompts"])


@pytest.mark.parametrize(("task", "name"), CASES)
def test_qa_sec_003_unchecked_supplement_is_sent_to_ai(client, recorder, task, name):
    """대조군: 체크를 해제하면 같은 값이 다시 만든 생성 요청에 실린다."""
    run = _draft_then_save_supplement(client, recorder, task, name, private=False)
    assert VALUE in _sent(run["new_prompts"])
