"""TC2 외부 메모리 동적 참조: 요청은 무상태, 세션은 바깥 저장소, 파이프라인은 참조만, 상한에 차면 넘치지 않고 503."""
from app.core.store import SqliteSessionStore
from app.harness import registry as registry_module
from app.harness.registry import TASK_TYPES
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer, answer_all, generate, start
from tests.conftest import api_client


def test_tc2_1_세션은_바깥_저장소에_있어_서버를_새로_띄워도_이어진다(tmp_path):
    """앱 A에서 시작한 세션을, 같은 DB 파일을 여는 다른 서버 인스턴스 B에서 이어 답하고 생성한다."""
    path = tmp_path / "sessions.db"
    first = api_client(create_app(provider=MockProvider(), store=SqliteSessionStore(path)))
    view = start(first, "business_plan")
    answer(first, view, "선물 고르기가 어렵다")

    second = api_client(create_app(provider=MockProvider(), store=SqliteSessionStore(path)))
    resumed = second.get(f"{BASE}/sessions/{view['session_id']}").json()
    assert any(item["value"] == "선물 고르기가 어렵다" for item in resumed["summary"])
    answer_all(second, resumed)
    assert generate(second, view["session_id"])["version"]["version"] == 1


def test_tc2_2_파이프라인은_과제마다_한_번만_만들고_요청은_참조만_한다(monkeypatch):
    """세션을 많이 만들어도 하네스 객체는 과제 수만큼이고 같은 객체를 쓰며, 요청 중 하네스를 다시 만들지 않는다."""
    app = create_app(provider=MockProvider())
    client = api_client(app)
    before = {h.task_type: id(h) for h in app.state.registry.all()}
    rebuilt: list[str] = []
    real_build = registry_module.build_harness

    def counting_build(task_type, *args, **kwargs):
        rebuilt.append(task_type)
        return real_build(task_type, *args, **kwargs)

    monkeypatch.setattr(registry_module, "build_harness", counting_build)
    for i in range(20):
        start(client, TASK_TYPES[i % len(TASK_TYPES)])
    after = {h.task_type: id(h) for h in app.state.registry.all()}
    assert len(after) == len(TASK_TYPES)
    assert before == after
    assert rebuilt == []


def test_tc2_3_AI_호출이_상한에_차도_넘치지_않고_503이며_조회는_막히지_않는다():
    """자리가 다 찬 동안 생성은 503(세션 그대로), 세션 목록·세션 조회는 바로 200."""
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    view = start(client, "branding")
    sid = view["session_id"]

    with slots.hold():
        busy = client.post(f"{BASE}/sessions/{sid}/generate")
        listed = client.get(f"{BASE}/sessions")
        shown = client.get(f"{BASE}/sessions/{sid}")

    assert busy.status_code == 503
    assert "retry-after" in busy.headers
    assert listed.status_code == 200 and [s["session_id"] for s in listed.json()] == [sid]
    assert shown.status_code == 200 and shown.json()["status"] == view["status"]
    assert shown.json()["has_result"] is False
