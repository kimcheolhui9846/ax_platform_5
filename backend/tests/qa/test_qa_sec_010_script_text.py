"""TC-SEC-010 (서버 쪽): 스크립트 문자열을 실행·변형하지 않고 글자 그대로 저장하고 돌려준다.

화면에서 알림창이 뜨는지는 사용자가 직접 확인한다. 프론트 위치 조사는 QA/results.md에 적는다.
"""
import pytest

from tests.acceptance.flow import BASE, answer, answer_all, generate, start

PAYLOADS = ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>"]


@pytest.mark.parametrize("payload", PAYLOADS)
def test_qa_sec_010_script_in_request_text_is_kept_verbatim(client, payload):
    view = start(client, "business_plan", payload)
    assert view["raw_input"] == payload
    assert client.get(f"{BASE}/sessions/{view['session_id']}").json()["raw_input"] == payload


@pytest.mark.parametrize("payload", PAYLOADS)
def test_qa_sec_010_script_in_free_text_answer_is_kept_verbatim(client, payload):
    view = start(client, "business_plan")
    field = view["next_question"]["field"]
    after = answer(client, view, payload)
    stored = client.get(f"{BASE}/sessions/{view['session_id']}").json()
    assert next(i for i in after["summary"] if i["field"] == field)["value"] == payload
    assert next(i for i in stored["summary"] if i["field"] == field)["value"] == payload


@pytest.mark.parametrize("payload", PAYLOADS)
def test_qa_sec_010_script_in_supplement_is_kept_verbatim(client, payload):
    view, _ = answer_all(client, start(client, "business_plan"))
    sid = view["session_id"]
    saved = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"sales_channel": payload}})
    assert saved.status_code == 200, saved.text
    assert next(s for s in saved.json()["supplements"] if s["name"] == "sales_channel")["value"] == payload
    generate(client, sid)  # 초안 생성도 오류 없이 끝난다
    stored = client.get(f"{BASE}/sessions/{sid}").json()
    assert next(s for s in stored["supplements"] if s["name"] == "sales_channel")["value"] == payload
