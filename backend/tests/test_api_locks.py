"""같은 세션을 바꾸는 요청은 한 번에 하나씩(마지막 저장이 앞선 변경을 덮어쓰지 않게)."""
import threading

import pytest
from tests.conftest import api_client

from app.api.locks import SessionLocks
from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/coaching"


def test_same_session_waits_for_the_holder():
    locks = SessionLocks()
    order: list[str] = []
    a_inside = threading.Event()
    release_a = threading.Event()

    def holder():
        with locks.hold("sess_1"):
            order.append("a 시작")
            a_inside.set()
            release_a.wait(timeout=5)
            order.append("a 끝")

    def waiter():
        a_inside.wait(timeout=5)
        with locks.hold("sess_1"):
            order.append("b")

    threads = [threading.Thread(target=holder), threading.Thread(target=waiter)]
    for t in threads:
        t.start()
    a_inside.wait(timeout=5)
    assert locks.is_held("sess_1")
    release_a.set()
    for t in threads:
        t.join(timeout=5)

    assert order == ["a 시작", "a 끝", "b"]
    assert not locks.is_held("sess_1")


def test_different_sessions_do_not_block_each_other():
    locks = SessionLocks()
    with locks.hold("sess_1"):
        done = threading.Event()

        def other():
            with locks.hold("sess_2"):
                done.set()

        t = threading.Thread(target=other)
        t.start()
        assert done.wait(timeout=5)
        t.join(timeout=5)


@pytest.mark.parametrize("route", ["answer", "revise", "generate", "continue"])
def test_mutating_routes_hold_the_session_lock_during_harness_call(monkeypatch, route):
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    view = client.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}).json()
    sid, qid = view["session_id"], view["next_question"]["question_id"]
    harness = app.state.registry.get("product_planning")
    seen: list[bool] = []

    if route == "revise":
        client.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": qid, "answer_type": "option", "option_ids": ["o1"]})

    method = {"answer": "apply_answer", "revise": "revise_answer", "generate": "generate", "continue": "resume"}[route]
    original = getattr(harness, method)

    def spy(*args, **kwargs):
        seen.append(app.state.locks.is_held(sid))
        return original(*args, **kwargs)

    monkeypatch.setattr(harness, method, spy)
    if route == "answer":
        response = client.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": qid, "answer_type": "skip"})
    elif route == "revise":
        response = client.patch(f"{BASE}/sessions/{sid}/answers/{qid}", json={"answer_type": "free_text", "value": "부모"})
    elif route == "continue":
        response = client.post(f"{BASE}/sessions/{sid}/continue")
    else:
        response = client.post(f"{BASE}/sessions/{sid}/generate")

    assert response.status_code == 200, response.text
    assert seen == [True]
    assert not app.state.locks.is_held(sid)


def test_unknown_session_ids_create_no_locks():
    app = create_app(provider=MockProvider(), debug=True)
    client = api_client(app)
    for i in range(3):
        sid = f"sess_없음{i}"
        assert client.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": "q", "answer_type": "skip"}).status_code == 404
        assert client.patch(f"{BASE}/sessions/{sid}/answers/q", json={"answer_type": "free_text", "value": "x"}).status_code == 404
        assert client.post(f"{BASE}/sessions/{sid}/generate").status_code == 404
        assert client.post(f"{BASE}/sessions/{sid}/continue").status_code == 404
    assert len(app.state.locks) == 0

    sid = client.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}).json()["session_id"]
    client.post(f"{BASE}/sessions/{sid}/continue")
    assert len(app.state.locks) == 1
