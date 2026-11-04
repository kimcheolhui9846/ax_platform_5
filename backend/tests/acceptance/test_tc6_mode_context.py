"""TC6 컨텍스트 메모리 모드별: 모드가 다른 세션은 서로 독립, 이어가기 컨텍스트는 모드와 상관없이 같다."""
import pytest

from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer, answer_all, finished, start
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
        answer(client, view, f"{mode} 전용 답")
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


def test_tc6_3_빠른_모드는_상한만큼_묻고_표준_모드는_더_묻는다(client):
    """정책의 모드별 상한(question_caps)을 읽어 확인한다. 빠른 모드는 상한을 모두 채우고 표준보다 적게 묻는다.
    정밀 모드의 상한(10)은 준비도가 먼저 차서 닿지 않으므로 '상한 이하'만 본다."""
    caps = client.app.state.registry.get("business_plan").policy.question_caps
    asked = {mode: set(answer_all(client, start(client, "business_plan", mode=mode))[1]) for mode in MODES}
    for mode in MODES:
        assert len(asked[mode]) <= caps[mode], f"{mode}: {len(asked[mode])} > {caps[mode]}"
    assert len(asked["quick"]) == caps["quick"]
    assert len(asked["quick"]) < len(asked["standard"])
