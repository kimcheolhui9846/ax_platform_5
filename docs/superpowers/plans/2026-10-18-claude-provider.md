# 실제 Claude 연결(LLM 제공자) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `PROVIDER=claude`로 하네스의 모든 LLM 단계(diagnose·easier_question·propose_value·generate·validate)를 실제 Claude로 돌린다. 테스트는 계속 Mock(가짜 SDK 클라이언트)으로 돌고 돈을 쓰지 않는다.

**Architecture:** `app/providers/claude.py`의 `ClaudeProvider`가 `LLMProvider` 계약(`complete(task_type, stage, prompt, response_model)`)을 구현한다. 공식 Python SDK `anthropic`의 `client.beta.messages.parse(..., output_format=response_model)`로 구조화 출력을 받고, `prompt.system`은 캐시되는 시스템 블록, `prompt.user`는 사용자 메시지로 보낸다. SDK 오류는 `ProviderError`, 스키마·중단·거절은 `ProviderOutputError`/`ProviderError`로 감싼다. 클라이언트는 생성자에서 주입받아(기본은 `anthropic.Anthropic()`) 테스트가 가짜를 넣는다.

**Tech Stack:** Python 3.12, `anthropic`(공식 SDK, 1.x), Pydantic v2, pytest.

## Global Constraints

- SDK 사용법은 claude-api 스킬 문서 그대로다(추측 금지): 클라이언트 `anthropic.Anthropic()`(키는 환경 변수 `ANTHROPIC_API_KEY`), 구조화 출력 `client.beta.messages.parse(model=..., max_tokens=..., system=[...], messages=[...], output_format=<Pydantic 모델>)` → `response.parsed_output`, `response.stop_reason`, `response.model`, `response.usage.input_tokens/output_tokens`. 오류 클래스 `anthropic.APIStatusError`·`anthropic.APIConnectionError`·`anthropic.APITimeoutError`(모두 `anthropic.APIError` 하위).
- 기본 모델 `claude-opus-5-5`(설정 `CLAUDE_MODEL`로 바꾼다). 이 모델은 thinking을 끌 수 없고(`thinking` 인자를 보내지 않는다), 노력은 `output_config={"effort": ...}`(기본값을 명시: 설정 `CLAUDE_EFFORT`, 기본 `medium`). `temperature` 등 샘플링 인자는 보내지 않는다(400).
- 거절 대비: 요청에 `betas=["server-side-fallback-2026-07-01"]`와 `fallbacks="default"`를 넣는다(Claude API 전용). `stop_reason == "refusal"`이면 `ProviderError`.
- 프롬프트 캐시: 시스템 블록에 `cache_control: {"type": "ephemeral"}`(과제마다 고정이라 캐시 앞부분).
- `max_tokens`: 16000(비스트리밍 기본). `stop_reason == "max_tokens"`면 `ProviderOutputError`(하네스가 생성 단계에서 한 번 다시 부른다).
- 비밀: API 키는 코드·로그·trace·커밋에 넣지 않는다. `backend/.env`는 읽거나 고치지 않는다(`backend/.env.example`만 고친다). 실제 API 호출은 테스트에서 하지 않는다.
- 커밋·PR에 AI 공동저자·생성 표기 금지. git 신원 `kim cheol hui <144594976+kimcheolhui9846@users.noreply.github.com>`.
- `CLAUDE.md` "비용" 절의 계약을 지킨다(`prompt.system` → system, `prompt.user` → user, `response_model`로 강제, SDK·파싱 오류 감싸기).

## 결정 사항 (컨트롤러)

1. **이미지·근거 검색은 그대로 Mock·샘플이다.** Claude는 이미지를 만들지 않는다. 웹 검색 근거(`find_evidence`)는 다음 작업으로 둔다(HANDOFF "다음 할 일").
2. **모델·노력은 설정 하나씩**(`CLAUDE_MODEL`, `CLAUDE_EFFORT`). 단계별로 다르게 하는 것은 튜닝 단계에서 측정 뒤 정한다.
3. **실제 호출 확인은 사용자가 키를 넣고 직접 한다.** `scripts/claude_smoke.py`(저장소 루트, 한 번에 세션 하나: 시작→생성)를 두고, 실행 방법과 대략의 비용을 HANDOFF에 적는다. pytest는 실제 호출을 하지 않는다.

---

### Task 1: ClaudeProvider와 설정·팩토리

**Files:**
- Modify: `backend/pyproject.toml`(`uv add --directory backend anthropic`, 잠금 파일 포함)
- Create: `backend/app/providers/claude.py`
- Modify: `backend/app/providers/factory.py`, `backend/app/config.py`, `backend/app/main.py`, `backend/.env.example`
- Test: `backend/tests/test_claude_provider.py` (새), `backend/tests/test_providers.py`(팩토리 테스트)
- Create: `scripts/claude_smoke.py`
- Modify: `CLAUDE.md`(구조의 providers 줄, "비용" 절), `docs/HANDOFF.md`(실제 연결 확인 방법)

**Interfaces:**
- Produces:
  - `ClaudeProvider(model: str, effort: str, client: Any | None = None)`, `name = "claude"`, `complete(*, task_type, stage, prompt, response_model=None) -> ProviderResponse`
  - `get_provider(name: str, *, model: str = DEFAULT_CLAUDE_MODEL, effort: str = DEFAULT_CLAUDE_EFFORT) -> LLMProvider`(`mock` | `claude`)
  - `Settings.claude_model: str = "claude-opus-5-5"`, `Settings.claude_effort: Literal["low","medium","high","xhigh","max"] = "medium"`

- [ ] **Step 1: 의존성** — `uv add --directory backend anthropic`. 설치된 버전에서 `anthropic.Anthropic().beta.messages.parse`의 인자(`output_format`, `betas`, `fallbacks`, `output_config`, `system`)를 `inspect.signature`로 확인한다. `fallbacks`가 시그니처에 없으면 `extra_body={"fallbacks": "default"}`로 보낸다(보고서에 적는다).

- [ ] **Step 2: 실패 테스트** — `backend/tests/test_claude_provider.py`. 가짜 클라이언트로 요청 모양과 응답·오류 변환을 확인한다:

```python
"""ClaudeProvider: 실제 SDK 대신 가짜 클라이언트로 요청 모양과 결과·오류 변환을 확인한다(돈을 쓰지 않는다)."""
from types import SimpleNamespace

import anthropic
import httpx2 as httpx  # anthropic 1.x는 httpx2를 쓴다(설치된 SDK가 httpx면 그것으로)
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderError, ProviderOutputError
from app.providers.claude import ClaudeProvider


class Answer(BaseModel):
    text: str


class FakeMessages:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.calls = result, error, []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.result


def fake_client(messages: FakeMessages):
    return SimpleNamespace(beta=SimpleNamespace(messages=messages))


def message(parsed=None, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        model="claude-opus-5-5",
        content=[SimpleNamespace(type="text", text='{"text": "안녕"}')],
        usage=SimpleNamespace(input_tokens=120, output_tokens=30),
    )


PROMPT = Prompt(system="고정된 과제 설명", user="세션 맥락")


def test_sends_system_as_a_cached_block_and_user_as_the_message():
    messages = FakeMessages(result=message(Answer(text="안녕")))
    provider = ClaudeProvider(model="claude-opus-5-5", effort="medium", client=fake_client(messages))

    response = provider.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=Answer)

    [call] = messages.calls
    assert call["model"] == "claude-opus-5-5"
    assert call["system"] == [{"type": "text", "text": "고정된 과제 설명", "cache_control": {"type": "ephemeral"}}]
    assert call["messages"] == [{"role": "user", "content": "세션 맥락"}]
    assert call["output_format"] is Answer
    assert call["output_config"] == {"effort": "medium"}
    assert call["max_tokens"] == 16000
    assert "thinking" not in call and "temperature" not in call
    assert response.parsed == Answer(text="안녕")
    assert (response.model, response.usage.input_tokens, response.usage.output_tokens) == ("claude-opus-5-5", 120, 30)


def test_opts_into_server_side_fallbacks():
    messages = FakeMessages(result=message(Answer(text="x")))
    ClaudeProvider(model="claude-opus-5-5", effort="low", client=fake_client(messages)).complete(
        task_type="t", stage="diagnose", prompt=PROMPT, response_model=Answer
    )
    call = messages.calls[0]
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call.get("fallbacks", call.get("extra_body", {}).get("fallbacks")) == "default"


@pytest.mark.parametrize(
    ("result", "error_type"),
    [
        (message(None, "refusal"), ProviderError),
        (message(None, "max_tokens"), ProviderOutputError),
        (message(None, "end_turn"), ProviderOutputError),
    ],
)
def test_unusable_responses_become_provider_errors(result, error_type):
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(result=result)))
    with pytest.raises(error_type):
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)


def test_refusal_is_not_an_output_error():
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(result=message(None, "refusal"))))
    with pytest.raises(ProviderError) as caught:
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)
    assert not isinstance(caught.value, ProviderOutputError)  # 다시 불러도 같으니 한 번 더 부르지 않게


def api_errors():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return [
        anthropic.APIConnectionError(request=request),
        anthropic.APITimeoutError(request=request),
        anthropic.RateLimitError("rate", response=httpx.Response(429, request=request), body=None),
        anthropic.InternalServerError("boom", response=httpx.Response(500, request=request), body=None),
        anthropic.AuthenticationError("key", response=httpx.Response(401, request=request), body=None),
    ]


@pytest.mark.parametrize("error", api_errors())
def test_sdk_errors_become_provider_errors(error):
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(error=error)))
    with pytest.raises(ProviderError) as caught:
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)
    assert not isinstance(caught.value, ProviderOutputError)


def test_schema_validation_failures_become_output_errors():
    from pydantic import ValidationError

    try:
        Answer.model_validate({})
    except ValidationError as error:
        invalid = error
    provider = ClaudeProvider(model="m", effort="medium", client=fake_client(FakeMessages(error=invalid)))
    with pytest.raises(ProviderOutputError):
        provider.complete(task_type="t", stage="generate", prompt=PROMPT, response_model=Answer)


def test_without_a_response_model_returns_the_text():
    messages = FakeMessages(result=message(None))
    # response_model이 없으면 구조화 출력 없이 글만 받는다(하네스는 언제나 모델을 넘기지만 계약상 선택이다)
    ...
```

마지막 테스트는 구현에 맞춰 완성한다: `response_model is None`이면 `client.beta.messages.create(...)`(같은 system·messages·output_config·fallbacks, `output_format` 없음)를 부르고 `ProviderResponse(text=첫 text 블록, parsed=None)`. 가짜 `FakeMessages`에 `create`를 더해 확인한다.

`test_providers.py`의 팩토리 테스트를 늘린다: `get_provider("claude", model="claude-haiku-5-5", effort="low")`는 `ClaudeProvider`(이름 `claude`, 모델·노력 반영)이고 실제 호출을 하지 않는다(생성만). 키가 없을 때 생성 자체가 실패하는 SDK라면 테스트에서 `monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")`. 모르는 이름의 오류 문구에 `claude`가 지원 목록으로 나온다.

- [ ] **Step 3: 실패 확인** — `uv run --directory backend pytest tests/test_claude_provider.py -q` → FAIL

- [ ] **Step 4: 구현** — `backend/app/providers/claude.py`:

```python
"""실제 Claude 제공자. 공식 SDK(anthropic)로 부르고, 결과와 오류를 LLMProvider 계약으로 바꾼다.

prompt.system은 과제마다 고정이라 캐시되는 시스템 블록, prompt.user는 사용자 메시지다. 출력 구조는
response_model로 강제한다(구조화 출력). 키는 환경 변수 ANTHROPIC_API_KEY에서 SDK가 읽는다.
"""
from typing import Any

import anthropic
from pydantic import BaseModel, ValidationError

from app.providers.base import Prompt, ProviderError, ProviderOutputError, ProviderResponse, Usage

MAX_TOKENS = 16000  # 비스트리밍 요청의 기본 상한(HTTP 시간 제한 안쪽)
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # 거절되면 서버가 권장 모델로 다시 돌린다


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str, effort: str, client: Any | None = None) -> None:
        self.model = model
        self.effort = effort
        self.client = client if client is not None else anthropic.Anthropic()

    def _request(self, prompt: Prompt) -> dict[str, Any]:
        return {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "system": [{"type": "text", "text": prompt.system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": prompt.user}],
            "output_config": {"effort": self.effort},
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: Prompt,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        try:
            if response_model is None:
                response = self.client.beta.messages.create(**self._request(prompt))
            else:
                response = self.client.beta.messages.parse(**self._request(prompt), output_format=response_model)
        except ValidationError as exc:
            raise ProviderOutputError(f"{stage} 단계 응답이 스키마를 통과하지 못했습니다: {exc.error_count()}개 오류") from exc
        except anthropic.APIError as exc:
            raise ProviderError(f"{stage} 단계 Claude 호출 실패: {type(exc).__name__}") from exc
        return _to_response(stage, response, response_model)


def _to_response(stage: str, response: Any, response_model: type[BaseModel] | None) -> ProviderResponse:
    """[순수] SDK 응답을 계약의 응답으로. 거절은 호출 실패, 잘림·빈 구조화 출력은 스키마 실패다."""
    if response.stop_reason == "refusal":
        raise ProviderError(f"{stage} 단계 요청을 Claude가 거절했습니다.")
    if response.stop_reason == "max_tokens":
        raise ProviderOutputError(f"{stage} 단계 응답이 길이 상한에서 잘렸습니다.")
    parsed = getattr(response, "parsed_output", None) if response_model is not None else None
    if response_model is not None and parsed is None:
        raise ProviderOutputError(f"{stage} 단계 응답에 구조화된 결과가 없습니다.")
    text = next((block.text for block in response.content if block.type == "text"), "")
    return ProviderResponse(
        text=text,
        model=response.model,
        parsed=parsed,
        usage=Usage(input_tokens=response.usage.input_tokens, output_tokens=response.usage.output_tokens),
    )
```

(오류 문구에 SDK 원문을 넣지 않는다 — trace에는 `str(exc)`가 남는데, 원문 메시지에 요청 내용이 들어갈 수 있어 예외 이름만 둔다. `__cause__`로 원문은 로그·디버그에서 볼 수 있다.)

`backend/app/config.py`의 `Settings`에:

```python
    claude_model: str = "claude-opus-5-5"  # PROVIDER=claude일 때 쓰는 모델
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"  # 생각 깊이·비용
```

`backend/app/providers/factory.py`:

```python
"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 여기에 한 줄씩 추가한다."""
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider

DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"
DEFAULT_CLAUDE_EFFORT = "medium"


def get_provider(name: str, *, model: str = DEFAULT_CLAUDE_MODEL, effort: str = DEFAULT_CLAUDE_EFFORT) -> LLMProvider:
    if name == "mock":
        return MockProvider()
    if name == "claude":
        from app.providers.claude import ClaudeProvider  # mock만 쓸 때는 SDK를 읽지 않는다

        return ClaudeProvider(model=model, effort=effort)
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: mock, claude)")
```

`backend/app/main.py`의 `get_provider(settings.provider)`를 `get_provider(settings.provider, model=settings.claude_model, effort=settings.claude_effort)`로.

`backend/.env.example`의 PROVIDER 줄을 바꾼다:

```
# 모델 제공자. mock(기본, 비용 0) 또는 claude(실제 호출, 비용 발생).
PROVIDER=mock
# PROVIDER=claude일 때: API 키는 이 파일이 아니라 환경 변수나 backend/.env에 ANTHROPIC_API_KEY로 넣는다(커밋 금지).
# CLAUDE_MODEL=claude-opus-5-5   # 더 싸게: claude-sonnet-5-5, claude-haiku-5-5
# CLAUDE_EFFORT=medium           # low | medium | high | xhigh | max
```

- [ ] **Step 5: 실제 확인 스크립트** — `scripts/claude_smoke.py`(사용자가 키를 넣고 직접 실행, 비용 발생):

```python
"""실제 Claude로 세션 하나를 끝까지 돌려 본다(비용 발생). 키는 환경 변수 ANTHROPIC_API_KEY.

실행(저장소 루트): uv run --directory backend python ../scripts/claude_smoke.py [과제] [요청 글]
  예) uv run --directory backend python ../scripts/claude_smoke.py product_planning "집들이 선물용 수제 향초"
진단 → 질문 하나에 '아직 모르겠어요' → 생성까지 돌리고, 단계별 모델·토큰과 결과 섹션 제목을 출력한다.
"""
```

본문: `from app.config import settings`; `from app.harness.registry import build_harness`; `from app.providers.claude import ClaudeProvider`; `harness = build_harness(task, ClaudeProvider(settings.claude_model, settings.claude_effort))`; `state = harness.start(raw)`; 걸린 질문이 있으면 `skip`으로 한 번 답(`harness.apply_answer(state, Answer(question_id=..., answer_type=AnswerType.SKIP))`); `harness.generate(state)`; trace 항목마다 `stage`, `model`, `usage`를 한 줄씩 출력하고 결과 섹션 제목, 검증 이슈 수, 상태를 출력. `GenerationFailed`면 마지막 trace의 `output.error`를 출력하고 종료 코드 1. 키나 내용은 출력하지 않는다. 이 스크립트는 테스트하지 않는다(실제 호출).

- [ ] **Step 6: 통과 확인** — `uv run --directory backend pytest -q` → PASS(전부). `PROVIDER` 기본은 `mock`이라 앱 테스트는 그대로다.

- [ ] **Step 7: 문서**
  - `CLAUDE.md` 구조의 providers 줄: "모델 제공자. `MockProvider`(기본, 비용 0)와 `ClaudeProvider`(`claude.py`, 공식 SDK `anthropic`, `PROVIDER=claude`, 모델 `CLAUDE_MODEL`·노력 `CLAUDE_EFFORT`, 키는 환경 변수 `ANTHROPIC_API_KEY`). …"로 고치고, "비용" 절에 "실제 호출 확인은 `scripts/claude_smoke.py`(사용자가 키를 넣고 실행). 거절되면 서버 측 대체 모델(`fallbacks: "default"`)로 다시 돌고, 그래도 거절이면 `ProviderError`(502)." 한 문장.
  - `docs/HANDOFF.md` "다음 할 일"의 실제 AI 연결 항목에서 LLM 연결을 완료로 옮기고, 키 넣는 법(`backend/.env`에 `PROVIDER=claude`, `ANTHROPIC_API_KEY=…` — 사용자가 직접), 스모크 실행 명령, 비용 감(모델별 단가: Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50 per 1M 토큰 입·출력)을 적는다.

- [ ] **Step 8: 커밋**

```bash
git add backend scripts CLAUDE.md docs/HANDOFF.md
git commit -m "실제 Claude 연결: ClaudeProvider(공식 SDK, 구조화 출력·캐시·거절 대체), PROVIDER=claude 설정과 확인 스크립트"
```
