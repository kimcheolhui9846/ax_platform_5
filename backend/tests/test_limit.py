"""AI 동시 호출 상한: 자리를 못 얻으면 기다렸다 ProviderBusy, 세션은 바뀌지 않고 API는 503."""
import pytest

from app.core.messages import AI_BUSY_MESSAGE
from app.core.state import SessionStatus
from app.harness.errors import GenerationFailed
from app.main import create_app
from app.providers.base import Prompt, ProviderBusy, ProviderError
from app.providers.image import MockImageProvider
from app.providers.limit import CallSlots, LimitedImageProvider, LimitedProvider
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness, api_client

PROMPT = Prompt(system="고정", user="맥락")
BASE = "/api/v1/coaching"


def test_slots_reject_after_wait_when_full():
    slots = CallSlots(size=1, wait_seconds=0)
    with slots.hold():
        with pytest.raises(ProviderBusy):
            with slots.hold():
                pass


def test_slots_return_after_use():
    slots = CallSlots(size=1, wait_seconds=0)
    with slots.hold():
        pass
    with slots.hold():
        pass


def test_slots_return_after_error():
    slots = CallSlots(size=1, wait_seconds=0)
    with pytest.raises(RuntimeError):
        with slots.hold():
            raise RuntimeError("안쪽 실패")
    with slots.hold():
        pass


@pytest.mark.parametrize("size", [0, -1])
def test_slots_need_positive_size(size):
    with pytest.raises(ValueError):
        CallSlots(size=size, wait_seconds=0)


def test_busy_is_provider_error():
    """보조 단계(LLM 검토·이미지)는 ProviderError처럼 경고로 줄인다."""
    assert issubclass(ProviderBusy, ProviderError)


def test_limited_provider_passes_through_inside_slot():
    inner = MockProvider()
    limited = LimitedProvider(inner, CallSlots(size=1, wait_seconds=0))
    response = limited.complete(task_type="branding", stage="diagnose", prompt=PROMPT)
    assert inner.calls == [("branding", "diagnose")]
    assert response.model == "mock"
    assert limited.name == inner.name


def test_limited_provider_skips_inner_when_busy():
    inner = MockProvider()
    slots = CallSlots(size=1, wait_seconds=0)
    limited = LimitedProvider(inner, slots)
    with slots.hold():
        with pytest.raises(ProviderBusy):
            limited.complete(task_type="branding", stage="diagnose", prompt=PROMPT)
    assert inner.calls == []


def test_limited_image_provider_shares_slots():
    inner = MockImageProvider()
    slots = CallSlots(size=1, wait_seconds=0)
    limited = LimitedImageProvider(inner, slots)
    assert limited.generate(task_type="branding", prompt=PROMPT).mime == "image/svg+xml"
    with slots.hold():
        with pytest.raises(ProviderBusy):
            limited.generate(task_type="branding", prompt=PROMPT)
    assert inner.calls == ["branding"]
    assert limited.name == inner.name


def test_generate_busy_rolls_back_without_failing():
    slots = CallSlots(size=1, wait_seconds=0)
    harness = SampleHarness(SAMPLE_TASK_DIR, LimitedProvider(MockProvider(), slots))
    state = harness.start("향초")
    before = state.model_dump(exclude={"trace"})

    with slots.hold():
        with pytest.raises(ProviderBusy):
            harness.generate(state)

    assert state.status is not SessionStatus.FAILED
    assert state.model_dump(exclude={"trace"}) == before


def test_generate_other_provider_error_still_fails():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED


@pytest.fixture
def slots():
    return CallSlots(size=1, wait_seconds=0)


@pytest.fixture
def client(slots):
    return api_client(create_app(provider=MockProvider(), slots=slots))


def _start(client):
    response = client.post(
        f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}
    )
    assert response.status_code == 201
    return response.json()


def test_api_create_session_is_503_when_busy(client, slots):
    with slots.hold():
        response = client.post(
            f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "향초"}
        )
    assert response.status_code == 503
    assert response.json() == {"detail": AI_BUSY_MESSAGE}
    assert response.headers["retry-after"] == "5"


def test_api_generate_is_503_when_busy_and_session_unchanged(client, slots):
    session = _start(client)
    sid = session["session_id"]
    with slots.hold():
        response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 503
    assert response.json() == {"detail": AI_BUSY_MESSAGE}
    after = client.get(f"{BASE}/sessions/{sid}").json()
    assert after["status"] == session["status"]
    assert after["error"] is None

    assert client.post(f"{BASE}/sessions/{sid}/generate").status_code == 200


def test_openapi_lists_503_wherever_502_is_listed(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path, operations in paths.items():
        for method, operation in operations.items():
            codes = set(operation["responses"])
            assert ("502" in codes) == ("503" in codes), f"{method.upper()} {path}"
