"""작업 정리 API: 삭제(결과 이미지까지)·이름 바꾸기·결과물에서 빼기. 남의 작업은 없는 작업과 같은 404다."""
import threading
import time

import pytest

from app.api.views import session_name
from app.core.assets import InMemoryAssetStore
from app.core.messages import ASSET_NOT_FOUND_MESSAGE, SESSION_NOT_FOUND_MESSAGE, VERSION_NOT_FOUND_MESSAGE
from app.core.results import ImageBlock, ImageOrigin, ResultSection
from app.core.state import SessionState, session_asset_ids
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import OTHER_CLIENT_ID, api_client

BASE = "/api/v1/coaching"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"/>'


@pytest.fixture
def app():
    return create_app(provider=MockProvider(), assets=InMemoryAssetStore(), debug=True)


@pytest.fixture
def client(app):
    return api_client(app)


def started(client, raw: str = "수제 향초") -> str:
    view = client.post(f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": raw}).json()
    sid, qid = view["session_id"], view["next_question"]["question_id"]
    client.post(f"{BASE}/sessions/{sid}/answers", json={"question_id": qid, "answer_type": "option", "option_ids": ["o2"]})
    return sid


def image_block(asset_id: str) -> ImageBlock:
    return ImageBlock(asset_id=asset_id, alt="a", caption="c", origin=ImageOrigin.AI_GENERATED)


def attach_image(app, sid: str) -> str:
    """지금 결과(=마지막 버전)의 첫 섹션에 파일 저장소에 둔 이미지를 붙인다."""
    store = app.state.store
    state = store.get(sid)
    asset_id = app.state.assets.put(state.owner_id, SVG, "image/svg+xml")
    for result in (state.result, state.versions[-1].result):
        result.sections[0].blocks.append(image_block(asset_id))
    store.save(state)
    return asset_id


# 삭제


def test_delete_removes_the_session_from_read_and_list(client):
    keep, gone = started(client), started(client, "다른 작업")

    response = client.delete(f"{BASE}/sessions/{gone}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"{BASE}/sessions/{gone}").status_code == 404
    assert [s["session_id"] for s in client.get(f"{BASE}/sessions").json()] == [keep]
    assert client.delete(f"{BASE}/sessions/{gone}").status_code == 404  # 두 번째는 없는 작업


def test_delete_removes_result_images(app, client):
    sid = started(client)
    client.post(f"{BASE}/sessions/{sid}/generate")
    asset_id = attach_image(app, sid)
    assert client.get(f"{BASE}/assets/{asset_id}").status_code == 200

    assert client.delete(f"{BASE}/sessions/{sid}").status_code == 204

    missing = client.get(f"{BASE}/assets/{asset_id}")
    assert (missing.status_code, missing.json()) == (404, {"detail": ASSET_NOT_FOUND_MESSAGE})


def test_delete_of_someone_elses_or_unknown_session_is_404(app, client):
    sid = started(client)
    other = api_client(app, client_id=OTHER_CLIENT_ID)

    for target in (sid, "sess_nope"):
        response = other.delete(f"{BASE}/sessions/{target}")
        assert (response.status_code, response.json()) == (404, {"detail": SESSION_NOT_FOUND_MESSAGE})

    assert client.get(f"{BASE}/sessions/{sid}").status_code == 200
    assert len(app.state.locks) == 1  # 없는 id로는 잠금이 늘지 않는다


def test_request_queued_behind_the_lock_gets_404_after_delete(app, client):
    sid = started(client)
    outcome: dict[str, int] = {}

    def rename() -> None:
        outcome["status"] = client.patch(f"{BASE}/sessions/{sid}", json={"name": "늦은 요청"}).status_code

    with app.state.locks.hold(sid):
        worker = threading.Thread(target=rename)
        worker.start()
        worker.join(timeout=0.3)
        assert worker.is_alive()  # 잠금에 막혀 기다린다
        app.state.store.delete(sid)  # 잠금을 쥔 쪽이 지운다
    worker.join(timeout=5)

    assert outcome == {"status": 404}  # 잠근 뒤 다시 읽으므로 지워진 작업은 404다
    assert client.get(f"{BASE}/sessions/{sid}").status_code == 404


def test_rename_after_delete_is_404(client):
    sid = started(client)
    assert client.delete(f"{BASE}/sessions/{sid}").status_code == 204
    assert client.patch(f"{BASE}/sessions/{sid}", json={"name": "x"}).status_code == 404


# 이름


def test_rename_strips_and_shows_in_summary_list_and_view(client):
    sid = started(client)

    response = client.patch(f"{BASE}/sessions/{sid}", json={"name": "  새 이름  "})

    assert response.status_code == 200
    assert response.json()["name"] == "새 이름"
    assert response.json()["session_id"] == sid
    assert client.get(f"{BASE}/sessions").json()[0]["name"] == "새 이름"
    assert client.get(f"{BASE}/sessions/{sid}").json()["name"] == "새 이름"


def test_name_defaults_to_the_first_line_of_the_request(client):
    sid = started(client, "  수제 향초\n둘째 줄")
    assert client.get(f"{BASE}/sessions/{sid}").json()["name"] == "수제 향초"


def test_rename_collapses_inner_whitespace_and_rejects_blank_whitespace(client):
    sid = started(client)

    renamed = client.patch(f"{BASE}/sessions/{sid}", json={"name": "a\nb\t  c"})
    assert (renamed.status_code, renamed.json()["name"]) == (200, "a b c")
    assert client.patch(f"{BASE}/sessions/{sid}", json={"name": "\t \n"}).status_code == 422


def test_rename_moves_the_work_to_the_top_of_the_list(client):
    first = started(client)
    time.sleep(0.05)  # Windows 시계는 거칠어 같은 순간으로 찍힐 수 있다
    second = started(client, "다른 작업")
    time.sleep(0.05)
    assert [s["session_id"] for s in client.get(f"{BASE}/sessions").json()] == [second, first]

    client.patch(f"{BASE}/sessions/{first}", json={"name": "새 이름"})

    # 이름을 바꾸는 것도 작업을 바꾼 것이라 목록 맨 위로 올라온다(updated_at이 갱신된다)
    assert [s["session_id"] for s in client.get(f"{BASE}/sessions").json()] == [first, second]


@pytest.mark.parametrize(("name", "status"), [("   ", 422), ("", 422), ("가" * 41, 422), ("가" * 40, 200), (" " + "가" * 40 + " ", 200)])
def test_rename_length_rules(client, name, status):
    sid = started(client)
    response = client.patch(f"{BASE}/sessions/{sid}", json={"name": name})
    assert response.status_code == status
    if status == 422:
        assert isinstance(response.json()["detail"], str)


def test_rename_of_someone_elses_session_is_404(app, client):
    sid = started(client)
    other = api_client(app, client_id=OTHER_CLIENT_ID)

    response = other.patch(f"{BASE}/sessions/{sid}", json={"name": "내 것"})

    assert (response.status_code, response.json()) == (404, {"detail": SESSION_NOT_FOUND_MESSAGE})
    assert client.get(f"{BASE}/sessions/{sid}").json()["name"] == "수제 향초"


# 결과물에서 빼기


def test_unsave_is_idempotent_and_leaves_the_result(client):
    sid = started(client)
    client.post(f"{BASE}/sessions/{sid}/generate")
    client.post(f"{BASE}/sessions/{sid}/versions/1/save")
    assert [v["version"] for v in client.get(f"{BASE}/sessions").json()[0]["saved_versions"]] == [1]

    first = client.delete(f"{BASE}/sessions/{sid}/versions/1/save")
    again = client.delete(f"{BASE}/sessions/{sid}/versions/1/save")

    assert (first.status_code, first.json()["saved_versions"]) == (200, [])
    assert (again.status_code, again.json()["saved_versions"]) == (200, [])
    assert first.json()["latest_version"] == 1
    assert client.get(f"{BASE}/sessions/{sid}/versions/1").json()["version"]["saved"] is False


def test_unsave_unknown_version_or_other_owner_is_404(app, client):
    sid = started(client)
    client.post(f"{BASE}/sessions/{sid}/generate")

    missing = client.delete(f"{BASE}/sessions/{sid}/versions/9/save")
    other = api_client(app, client_id=OTHER_CLIENT_ID).delete(f"{BASE}/sessions/{sid}/versions/1/save")

    assert (missing.status_code, missing.json()) == (404, {"detail": VERSION_NOT_FOUND_MESSAGE})
    assert (other.status_code, other.json()) == (404, {"detail": SESSION_NOT_FOUND_MESSAGE})


# 순수 함수


def test_session_name_prefers_the_name_then_the_first_line():
    assert session_name(SessionState(task_type="t", raw_input="a", name="이름")) == "이름"
    assert session_name(SessionState(task_type="t", raw_input="  첫 줄 \n둘째")) == "첫 줄"
    assert session_name(SessionState(task_type="t", raw_input="가" * 60)) == "가" * 40
    assert session_name(SessionState(task_type="t", raw_input="")) == ""


def test_session_asset_ids_collects_every_version_and_the_current_result(harness):
    state = harness.start("향초")
    harness.generate(state)
    harness.generate(state)
    for version, asset_id in zip(state.versions, ("asset_a", "asset_b")):
        version.result.sections[0].blocks.append(image_block(asset_id))
    state.result = state.versions[-1].result

    assert session_asset_ids(state) == {"asset_a", "asset_b"}
    assert session_asset_ids(SessionState(task_type="t")) == set()
    assert isinstance(state.result.sections[0], ResultSection)
