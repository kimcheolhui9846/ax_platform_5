"""내 세션 목록(GET /sessions): 내 것만, 최근에 바뀐 순서로, 이어서 작업·결과물 목록에 필요한 값."""
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import OTHER_CLIENT_ID, api_client

BASE = "/api/v1/coaching"


def create(client, task_type: str, raw_input: str) -> dict:
    return client.post(f"{BASE}/tasks/{task_type}/sessions", json={"notice_acknowledged": True, "raw_input": raw_input}).json()


def test_lists_only_my_sessions_newest_first(clock):
    app = create_app(provider=MockProvider(), debug=True)
    mine, theirs = api_client(app), api_client(app, client_id=OTHER_CLIENT_ID)
    older = create(mine, "branding", "한글 파우치 브랜드")
    newer = create(mine, "product_planning", "한글 파우치")
    create(theirs, "branding", "남의 세션")

    listed = mine.get(f"{BASE}/sessions").json()

    assert [s["session_id"] for s in listed] == [newer["session_id"], older["session_id"]]
    first = listed[0]
    assert (first["task_type"], first["title"], first["raw_input"], first["mode"]) == (
        "product_planning",
        "상품기획",
        "한글 파우치",
        "standard",
    )
    assert (first["has_question"], first["has_result"], first["result_stale"]) == (True, False, False)
    assert (first["latest_version"], first["saved_versions"]) == (None, [])
    assert first["updated_at"]


def test_summary_shows_versions_and_saved_ones():
    client = api_client(create_app(provider=MockProvider(), debug=True))
    sid = create(client, "product_planning", "한글 파우치")["session_id"]
    client.post(f"{BASE}/sessions/{sid}/generate")
    client.post(f"{BASE}/sessions/{sid}/generate")
    client.post(f"{BASE}/sessions/{sid}/versions/1/save")

    [summary] = client.get(f"{BASE}/sessions").json()

    assert (summary["has_result"], summary["latest_version"]) == (True, 2)
    assert [(v["version"], v["reason"], v["saved"]) for v in summary["saved_versions"]] == [(1, "first", True)]


def test_answering_moves_a_session_to_the_top(clock):
    client = api_client(create_app(provider=MockProvider(), debug=True))
    first = create(client, "branding", "브랜드")
    create(client, "product_planning", "상품")

    question = first["next_question"]
    client.post(
        f"{BASE}/sessions/{first['session_id']}/answers",
        json={"question_id": question["question_id"], "answer_type": "skip"},
    )

    assert client.get(f"{BASE}/sessions").json()[0]["session_id"] == first["session_id"]


def test_registry_knows_its_tasks():
    registry = create_app(provider=MockProvider()).state.registry
    assert "branding" in registry
    assert "없는_과제" not in registry
