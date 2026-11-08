"""TC-PERF-020: 아주 긴 입력(5,000자)이 그대로 AI로 보내져 요청 크기가 무한정 커지지 않는다.

ⓐ '내 요청' 글, ⓑ 질문의 직접 답변 두 길목을 본다.
ⓑ 판정(사용자 기준): 422로 거절하거나 잘라서 AI 요청 크기가 제한되면 PASS, 5,000자가 그대로 실리면 FAIL.
"""
from tests.acceptance.flow import BASE, start

LONG = ("가" * 99 + "\n") * 50  # 5,000자
assert len(LONG) == 5000


def test_qa_perf_020_long_request_text_is_rejected_before_ai(client, recorder):
    response = client.post(
        f"{BASE}/tasks/business_plan/sessions",
        json={"raw_input": LONG, "notice_acknowledged": True, "mode": "standard"},
    )
    assert response.status_code == 422
    assert recorder.prompts == []  # AI를 한 번도 부르지 않았다


def test_qa_perf_020_long_free_text_answer_does_not_reach_ai_as_is(client, recorder):
    view = start(client, "business_plan")
    question = view["next_question"]
    before = len(recorder.prompts)

    response = client.post(
        f"{BASE}/sessions/{view['session_id']}/answers",
        json={"question_id": question["question_id"], "answer_type": "free_text", "value": LONG},
    )

    if response.status_code == 422:
        assert len(recorder.prompts) == before  # 거절이면 AI를 부르지 않아야 한다
        return
    assert response.status_code == 200, response.text
    # 받아들였다면 이어지는 AI 요청에 5,000자가 그대로 실리면 안 된다(잘려서 제한돼야 한다)
    generate = client.post(f"{BASE}/sessions/{view['session_id']}/generate")
    assert generate.status_code == 200, generate.text
    sent = recorder.prompts[before:]
    assert sent, "답 이후 AI 요청이 없습니다"
    # 템플릿 필터(| inline)가 줄바꿈을 지우므로 글자 그대로 찾지 않고 '가'의 개수(원래 4,950개)로 센다
    carried = {stage: (p.system + p.user).count("가") for stage, p in sent}
    whole = {stage: n for stage, n in carried.items() if n >= LONG.count("가")}
    assert whole == {}, f"5,000자 답이 그대로 실린 단계(단계: '가' 개수): {whole}"
