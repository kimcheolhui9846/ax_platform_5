"""인수 테스트 공통 흐름: 사용자가 API로 하는 순서(시작 → 답하기 → 생성)를 그대로 따라간다."""
from fastapi.testclient import TestClient

BASE = "/api/v1/coaching"
DEFAULT_RAW = "한글 디자인 굿즈를 팔고 싶어요"


def start(client: TestClient, task: str, raw: str = DEFAULT_RAW, mode: str = "standard", **extra) -> dict:
    """세션을 만든다(외부 전송 안내 확인 포함). 201이 아니면 실패."""
    response = client.post(
        f"{BASE}/tasks/{task}/sessions",
        json={"notice_acknowledged": True, "raw_input": raw, "mode": mode, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def answer_all(client: TestClient, view: dict, limit: int = 15) -> tuple[dict, list[str]]:
    """걸린 질문이 없어질 때까지 자유 입력으로 답한다. (마지막 세션 화면, 물어본 필드 순서)."""
    asked: list[str] = []
    for step in range(limit):
        question = view["next_question"]
        if question is None:
            return view, asked
        asked.append(question["field"])
        response = client.post(
            f"{BASE}/sessions/{view['session_id']}/answers",
            json={"question_id": question["question_id"], "answer_type": "free_text", "value": f"테스트 답 {step + 1}"},
        )
        assert response.status_code == 200, response.text
        view = response.json()
    raise AssertionError(f"질문이 {limit}번 안에 끝나지 않았습니다: {asked}")


def generate(client: TestClient, session_id: str) -> dict:
    response = client.post(f"{BASE}/sessions/{session_id}/generate")
    assert response.status_code == 200, response.text
    return response.json()


def finished(client: TestClient, task: str, raw: str = DEFAULT_RAW) -> str:
    """시작 → 끝까지 답 → 생성까지 마친 세션 id."""
    view, _ = answer_all(client, start(client, task, raw))
    generate(client, view["session_id"])
    return view["session_id"]
