"""TC8 결과 생성: 생성 → 결과(섹션·버전 1) → 저장 → 결과물 목록. 다시 생성하면 버전 2."""
from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, generate, start
from tests.conftest import api_client


def test_tc8_1_생성하면_섹션이_있는_결과와_버전_1이_생기고_저장하면_결과물에_모인다():
    client = api_client(create_app(provider=MockProvider()))
    view, _ = answer_all(client, start(client, "ir_pitch", "한글 굿즈 시드 투자"))
    sid = view["session_id"]
    result = generate(client, sid)
    assert result["result"]["sections"]
    assert result["result"]["full_text"]
    number = result["version"]["version"]
    assert number == 1

    saved = client.post(f"{BASE}/sessions/{sid}/versions/{number}/save")
    assert saved.status_code == 200
    summary = next(s for s in client.get(f"{BASE}/sessions").json() if s["session_id"] == sid)
    assert [v["version"] for v in summary["saved_versions"]] == [1]


def test_tc8_2_다시_생성하면_버전이_쌓이고_지난_버전을_다시_볼_수_있다():
    client = api_client(create_app(provider=MockProvider()))
    view, _ = answer_all(client, start(client, "business_plan"))
    sid = view["session_id"]
    generate(client, sid)
    assert generate(client, sid)["version"]["version"] == 2
    first = client.get(f"{BASE}/sessions/{sid}/versions/1")
    assert first.status_code == 200
