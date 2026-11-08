"""TC-SEC-001: '내 요청'에 적은 전화번호가 가려진 채 처리된다(AI 요청 전에 가림)."""
from tests.acceptance.flow import BASE, answer_all, generate, start

PHONE = "010-0000-0000"
RAW = f"이 상품을 팔고 싶어요 {PHONE}으로 연락 주세요."


def test_qa_sec_001_phone_in_request_is_masked_before_every_ai_call(client, recorder):
    view, _ = answer_all(client, start(client, "business_plan", RAW))
    generate(client, view["session_id"])

    assert recorder.prompts, "AI 요청이 없었습니다"
    assert "generate" in recorder.stages()
    assert PHONE not in recorder.outbound_text()  # 진단·질문·생성 모든 AI 요청(system+user)에 원래 번호가 없다
    assert "[전화번호]" in recorder.outbound_text("generate")  # 대신 가림 표시가 실린다
    trace_redactions = client.get(f"{BASE}/sessions/{view['session_id']}/result")
    assert trace_redactions.status_code == 200
    assert PHONE not in trace_redactions.text  # AI 결과(초안)에 원래 번호가 나오지 않는다


def test_qa_sec_001_request_echo_is_shown_masked(client):
    """TC 예상 결과의 '가려진 상태로 표시': 다음 화면의 '내가 보낸 요청'(세션 응답 raw_input)도 가려져 있는가."""
    view = start(client, "business_plan", RAW)
    assert PHONE not in view["raw_input"]
