"""TC5 DB 생성 호출 상한: 세션 생성(진단 AI 호출 포함)에도 동시 호출 상한이 걸리고, 붐비면 DB에 작업이 생기지 않는다."""
import threading
import time

from app.core.store import InMemorySessionStore
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, start
from tests.conftest import api_client

BODY = {"notice_acknowledged": True, "raw_input": "향초"}


class SlowProvider(MockProvider):
    """AI 호출이 오래 걸리는 상황(실제 모델)을 흉내 낸다."""

    def complete(self, *args, **kwargs):
        time.sleep(0.3)
        return super().complete(*args, **kwargs)


def test_tc5_1_붐비면_세션_생성은_503이고_DB에_작업이_생기지_않는다():
    slots = CallSlots(size=1, wait_seconds=0)
    store = InMemorySessionStore()
    client = api_client(create_app(provider=MockProvider(), store=store, slots=slots))
    with slots.hold():
        response = client.post(f"{BASE}/tasks/product_planning/sessions", json=BODY)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert client.get(f"{BASE}/sessions").json() == []


def test_tc5_2_자리가_나면_같은_요청이_성공해_한_건만_저장된다():
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    with slots.hold():
        assert client.post(f"{BASE}/tasks/product_planning/sessions", json=BODY).status_code == 503
    view = start(client, "product_planning", "향초")
    assert [s["session_id"] for s in client.get(f"{BASE}/sessions").json()] == [view["session_id"]]


def test_tc5_3_동시에_몰리면_상한만큼만_통과하고_성공한_수만큼만_저장된다():
    """자리 2개·대기 0초에서 6개가 동시에 오면 일부는 503, 저장된 작업 수 = 201 응답 수."""
    slots = CallSlots(size=2, wait_seconds=0)
    app = create_app(provider=SlowProvider(), slots=slots)
    codes: list[int] = []
    lock = threading.Lock()
    barrier = threading.Barrier(6)

    def create() -> None:
        client = api_client(app)
        barrier.wait()
        code = client.post(f"{BASE}/tasks/product_planning/sessions", json=BODY).status_code
        with lock:
            codes.append(code)

    threads = [threading.Thread(target=create) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert set(codes) <= {201, 503}
    assert 1 <= codes.count(201) <= 6 and codes.count(503) >= 1
    saved = api_client(app).get(f"{BASE}/sessions").json()
    assert len(saved) == codes.count(201)
