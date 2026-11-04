"""TC6 컨텍스트 메모리 모드별: 모드가 다른 세션은 서로 독립, 이어가기 컨텍스트는 모드와 상관없이 같다."""
import pytest

from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, finished, start
from tests.conftest import api_client

MODES = ["quick", "standard", "precise"]


@pytest.fixture
def client():
    return api_client(create_app(provider=MockProvider()))


def values(view: dict) -> set[str]:
    return {item["value"] for item in view["summary"]}


def test_tc6_1_모드가_다른_세션은_서로의_답을_보지_않는다(client):
    views = {mode: start(client, "business_plan", f"{mode} 모드 아이디어", mode=mode) for mode in MODES}
    for mode, view in views.items():
        question = view["next_question"]
        client.post(
            f"{BASE}/sessions/{view['session_id']}/answers",
            json={"question_id": question["question_id"], "answer_type": "free_text", "value": f"{mode} 전용 답"},
        )
    for mode, view in views.items():
        seen = values(client.get(f"{BASE}/sessions/{view['session_id']}").json())
        assert f"{mode} 전용 답" in seen and f"{mode} 모드 아이디어" in seen
        for other in MODES:
            if other != mode:
                assert f"{other} 전용 답" not in seen and f"{other} 모드 아이디어" not in seen


def test_tc6_2_이어가기_컨텍스트는_모드와_상관없이_똑같이_들어간다(client):
    prev = finished(client, "business_plan", "한글 디자인 북백 사업")
    carried = {}
    for mode in MODES:
        view = start(client, "ir_pitch", "투자 발표 준비", mode=mode, from_session_id=prev)
        assert view["mode"] == mode
        carried[mode] = sorted(
            (item["field"], item["value"]) for item in view["summary"] if item["source"] == "previous_task"
        )
    assert carried["quick"], "가져온 값이 없습니다"
    assert carried["quick"] == carried["standard"] == carried["precise"]


def test_tc6_3_모드마다_질문_상한이_다르게_적용된다(client):
    caps = {"quick": 3, "standard": 5, "precise": 10}
    for mode in MODES:
        _, asked = answer_all(client, start(client, "business_plan", mode=mode))
        assert len(set(asked)) <= caps[mode]
    _, quick = answer_all(client, start(client, "business_plan", mode="quick"))
    _, precise = answer_all(client, start(client, "business_plan", mode="precise"))
    assert len(set(quick)) <= len(set(precise))
