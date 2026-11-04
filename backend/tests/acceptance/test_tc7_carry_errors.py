"""TC7 다음 과제로 이어가기 오류: 실패해도 새 작업이 잘못 생기지 않고, 가져온 값은 빼거나 비공개로 지킨다."""
import pytest

from app.core.messages import (
    AI_BUSY_MESSAGE,
    PREVIOUS_SESSION_NOT_FOUND_MESSAGE,
    RESULT_NOT_READY_MESSAGE,
    VERSION_NOT_FOUND_MESSAGE,
)
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer, answer_all, finished, generate, start
from tests.conftest import OTHER_CLIENT_ID, api_client


def create(client, **extra):
    return client.post(
        f"{BASE}/tasks/ir_pitch/sessions",
        json={"notice_acknowledged": True, "raw_input": "투자 발표 준비", **extra},
    )


def session_ids(client) -> list[str]:
    return [s["session_id"] for s in client.get(f"{BASE}/sessions").json()]


@pytest.fixture
def app():
    return create_app(provider=MockProvider())


def test_tc7_1_남의_이전_작업이나_없는_작업은_404이고_새_작업이_생기지_않는다(app):
    mine = api_client(app)
    prev = finished(mine, "business_plan")
    other = api_client(app, client_id=OTHER_CLIENT_ID)
    for client, source in ((other, prev), (mine, "sess_없는작업")):
        before = session_ids(client)
        response = create(client, from_session_id=source)
        assert (response.status_code, response.json()) == (404, {"detail": PREVIOUS_SESSION_NOT_FOUND_MESSAGE})
        assert session_ids(client) == before


def test_tc7_2_결과가_없는_이전_작업은_404(app):
    client = api_client(app)
    prev = start(client, "business_plan")["session_id"]
    response = create(client, from_session_id=prev)
    assert (response.status_code, response.json()) == (404, {"detail": RESULT_NOT_READY_MESSAGE})


def test_tc7_3_없는_버전은_404_버전_0은_422(app):
    client = api_client(app)
    prev = finished(client, "business_plan")
    missing = create(client, from_session_id=prev, from_version=9)
    assert (missing.status_code, missing.json()) == (404, {"detail": VERSION_NOT_FOUND_MESSAGE})
    assert create(client, from_session_id=prev, from_version=0).status_code == 422


def test_tc7_4_AI가_붐비면_503이고_새_작업이_생기지_않는다():
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    prev = finished(client, "business_plan")
    before = session_ids(client)
    with slots.hold():
        response = create(client, from_session_id=prev)
    assert (response.status_code, response.json()) == (503, {"detail": AI_BUSY_MESSAGE})
    assert session_ids(client) == before


def test_tc7_5_가져온_내용을_빼면_이전_과제_값이_사라진다(app):
    client = api_client(app)
    prev = finished(client, "business_plan", "한글 디자인 북백 사업")
    view = start(client, "ir_pitch", "투자 발표 준비", from_session_id=prev)
    assert any(item["source"] == "previous_task" for item in view["summary"])
    cleared = client.delete(f"{BASE}/sessions/{view['session_id']}/context")
    assert cleared.status_code == 200
    assert all(item["source"] != "previous_task" for item in cleared.json()["summary"])
    assert cleared.json()["context"] is None


def test_tc7_6_사용자가_비공개로_정한_답은_다음_과제에서도_비공개다(app):
    """사업계획에서 '이 답은 AI에 보내지 않기'를 고른 답은 IR의 같은 내용(problem)으로 넘어와도 비공개로 남는다."""
    client = api_client(app)
    view = start(client, "business_plan", "한글 디자인 북백 사업")
    first = view["next_question"]
    assert first["field"] == "customer_problem"
    view = answer(client, view, "비밀 고객 문제", private=True)
    view, _ = answer_all(client, view)
    prev = view["session_id"]
    generate(client, prev)

    carried = start(client, "ir_pitch", "투자 발표 준비", from_session_id=prev)
    assert any(i["field"] == "problem" and i["source"] == "previous_task" for i in carried["summary"])
    assert "problem" in carried["private_names"]

    preview = client.get(f"{BASE}/tasks/ir_pitch/context", params={"session_id": prev}).json()
    assert [i["private"] for i in preview["items"] if i["field"] == "problem"] == [True]
