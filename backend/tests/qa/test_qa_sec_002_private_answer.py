"""TC-SEC-002: 직접 답변에 'AI에 보내지 않기'를 체크하면 그 답이 AI 요청에서 빠진다."""
from app.harness.privacy import PRIVATE_MARK
from tests.acceptance.flow import BASE, answer, answer_all, generate, start

MARKER = "TEST-NOAI-7777"


def _answer_first_then_rest(client, private: bool) -> str:
    view = start(client, "business_plan")
    view = answer(client, view, MARKER, private=private)
    view, _ = answer_all(client, view)
    generate(client, view["session_id"])
    return view["session_id"]


def test_qa_sec_002_checked_answer_is_not_sent_to_ai(client, recorder):
    sid = _answer_first_then_rest(client, private=True)

    # 세션에는 사용자가 쓴 값이 그대로 남아 있다(가림은 나가는 프롬프트에만)
    summary = client.get(f"{BASE}/sessions/{sid}").json()["summary"]
    assert any(item["value"] == MARKER and item["private"] for item in summary)

    assert "generate" in recorder.stages()
    assert MARKER not in recorder.outbound_text()  # 답한 뒤 모든 AI 요청(system+user)에 없다
    assert PRIVATE_MARK in recorder.outbound_text("generate")  # 대신 가림 표시가 실린다


def test_qa_sec_002_unchecked_answer_is_sent_to_ai(client, recorder):
    """대조군: 체크하지 않으면 같은 값이 생성 요청에 실린다(위 테스트가 헛돌지 않음을 보인다)."""
    _answer_first_then_rest(client, private=False)
    assert MARKER in recorder.outbound_text("generate")
