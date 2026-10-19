import pytest
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness, api_client

from app.core.messages import PROMPT_LEAK_MESSAGE
from app.core.state import AnswerType, SessionStatus
from app.harness.errors import PromptLeakError
from app.harness.untrusted import LEAK_MIN_CHARS, output_texts
from app.main import create_app
from app.providers.base import ProviderResponse
from app.providers.mock import MockProvider

BASE = "/api/v1/coaching"


def _replace_nth_string(value, text, n):
    """value 안의 n번째(0부터, 깊이 우선 순서) 문자열을 text로 바꾼 사본."""
    counter = [n]

    def walk(item):
        if isinstance(item, str):
            counter[0] -= 1
            return text if counter[0] == -1 else item
        if isinstance(item, dict):
            return {key: walk(sub) for key, sub in item.items()}
        if isinstance(item, list):
            return [walk(sub) for sub in item]
        return item

    return walk(value)


def _with_leak(model, text, response_model):
    """문자열 값을 차례로 text로 바꿔 보고, 스키마(열거형·길이)를 통과하는 첫 사본을 돌려준다."""
    data = model.model_dump()
    for n in range(len(output_texts(model))):
        try:
            return response_model.model_validate(_replace_nth_string(data, text, n))
        except ValueError:
            continue
    raise AssertionError("유출 줄을 넣을 문자열 필드가 없다")


def leaked_line(system: str) -> str:
    return next(
        line
        for line in (raw.lstrip("-# ").strip() for raw in system.splitlines())
        if len(line) >= LEAK_MIN_CHARS
    )


class LeakingProvider(MockProvider):
    """leak_stages 단계에서 system 프롬프트의 긴 줄을 그대로 결과에 넣는다."""

    def __init__(self, leak_stages: set[str] | None = None) -> None:
        super().__init__()
        self.leak_stages: set[str] = leak_stages or set()
        self.leaked: str | None = None

    def complete(self, *, task_type, stage, prompt, response_model=None):
        response = super().complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)
        if stage not in self.leak_stages:
            return response
        self.leaked = leaked_line(prompt.system)
        parsed = _with_leak(response.parsed, self.leaked, response_model)
        return ProviderResponse(text="{}", model=response.model, parsed=parsed)


def _snapshot(state):
    return state.model_dump(exclude={"trace"})


def test_generate_leak_raises_and_rolls_back_session():
    provider = LeakingProvider({"generate"})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    before = _snapshot(state)

    with pytest.raises(PromptLeakError):
        harness.generate(state)

    assert _snapshot(state) == before
    assert state.result is None and state.versions == []
    assert state.status is not SessionStatus.FAILED
    last = state.trace[-1]
    assert last.stage == "generate"
    assert last.output["error"] == "prompt_leak" and last.output["lines"] >= 1
    assert provider.leaked not in str(last.output)


def test_easier_question_leak_raises_and_keeps_session(reply):
    provider = LeakingProvider({"easier_question"})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    reply(harness, state, AnswerType.EASIER)
    reply(harness, state, AnswerType.EASIER)
    before = _snapshot(state)

    with pytest.raises(PromptLeakError):
        reply(harness, state, AnswerType.EASIER)

    assert provider.leaked is not None
    assert _snapshot(state) == before
    assert state.trace[-1].output["error"] == "prompt_leak"


def test_no_leak_generates_normally():
    harness = SampleHarness(SAMPLE_TASK_DIR, LeakingProvider())
    state = harness.start("향초")
    harness.generate(state)
    assert state.status is SessionStatus.COMPLETED


def test_api_generate_leak_is_422():
    client = api_client(create_app(provider=LeakingProvider({"generate"}), debug=True))
    created = client.post(
        f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "수제 향초"}
    )
    assert created.status_code == 201, created.text
    sid = created.json()["session_id"]

    response = client.post(f"{BASE}/sessions/{sid}/generate")

    assert response.status_code == 422
    assert response.json() == {"detail": PROMPT_LEAK_MESSAGE}


def test_validate_leak_becomes_warning_and_keeps_result():
    provider = LeakingProvider({"validate"})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    harness.policy.llm_validation = True
    state = harness.start("향초")

    harness.generate(state)

    assert provider.leaked is not None
    assert state.status is SessionStatus.COMPLETED
    assert len(state.versions) == 1
    assert "llm_review_unavailable" in [i.rule for i in state.validation.issues]
    leaks = [t for t in state.trace if t.stage == "validate" and t.output.get("error") == "prompt_leak"]
    assert len(leaks) == 1


def test_leak_is_logged_without_content(caplog):
    provider = LeakingProvider({"generate"})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    with caplog.at_level("WARNING"), pytest.raises(PromptLeakError):
        harness.generate(state)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "generate" in messages and provider.leaked not in messages


def test_api_session_creation_leak_is_422_and_saves_nothing():
    client = api_client(create_app(provider=LeakingProvider({"diagnose"}), debug=True))

    response = client.post(
        f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "수제 향초"}
    )

    assert response.status_code == 422
    assert response.json() == {"detail": PROMPT_LEAK_MESSAGE}
    assert client.get(f"{BASE}/sessions").json() == []


def test_api_easier_answer_leak_is_422_and_keeps_session():
    provider = LeakingProvider()
    client = api_client(create_app(provider=provider, debug=True))
    view = client.post(
        f"{BASE}/tasks/product_planning/sessions", json={"notice_acknowledged": True, "raw_input": "수제 향초"}
    ).json()
    sid = view["session_id"]
    provider.leak_stages = {"easier_question"}
    response = None
    for _ in range(8):
        before = client.get(f"{BASE}/sessions/{sid}").json()
        question = before["next_question"]
        response = client.post(
            f"{BASE}/sessions/{sid}/answers", json={"question_id": question["question_id"], "answer_type": "easier"}
        )
        if response.status_code == 422:
            break
        assert response.status_code == 200, response.text
    assert response.status_code == 422
    assert response.json() == {"detail": PROMPT_LEAK_MESSAGE}
    assert client.get(f"{BASE}/sessions/{sid}").json() == before
