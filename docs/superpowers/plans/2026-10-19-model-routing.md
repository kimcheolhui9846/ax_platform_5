# 단계별 모델 라우팅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 단계마다 Claude 모델·노력을 설정(`CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`)으로 고를 수 있게 하고(기본 꺼짐), 인수 기업이 알아야 할 내용을 README에 모은다.

**Architecture:** 순수 함수 `stage_targets`가 설정에서 단계 → (모델, 노력)을 고르고, `RoutedProvider`가 단계 이름으로 제공자를 골라 넘긴다. `get_provider`가 설정이 있을 때만 감싼다. 하네스·`_call`·trace 형식은 바뀌지 않는다.

**Tech Stack:** Python 3.12, pydantic-settings, anthropic SDK 1.x(httpx2), pytest.

설계: `docs/superpowers/specs/2026-10-19-model-routing-design.md`

## Global Constraints

- 환경 변수 이름: `CLAUDE_STAGE_MODELS`, `CLAUDE_STAGE_EFFORTS`(둘 다 JSON 객체). 설정 필드: `claude_stage_models: dict[str, str] = {}`, `claude_stage_efforts: dict[str, Effort] = {}`.
- `Effort = Literal["low", "medium", "high", "xhigh", "max"]` — 한 곳에 정의하고 `claude_effort`도 이 타입을 쓴다.
- 라우팅할 수 있는 단계: `prompting.STAGES`에서 `image`를 뺀 것(`diagnose`, `easier_question`, `propose_value`, `generate`, `validate`). 다른 키는 설정을 만들 때 실패한다.
- 기본값은 꺼짐: 두 설정이 비어 있으면 `get_provider("claude", ...)`는 지금처럼 `ClaudeProvider` 하나를 돌려준다(감싸지 않는다).
- `PROVIDER=mock`이면 단계 설정과 상관없이 `MockProvider`.
- 테스트는 실제 호출 없이(가짜 제공자, SDK 클라이언트 + httpx2 MockTransport). 키 값은 출력하지 않는다.
- 백엔드 테스트 `uv run --directory backend pytest -q`(저장소 루트에서).
- 커밋 메시지는 한국어, AI 공동저자 표기 금지. 순수 함수 docstring은 `[순수]`로 시작한다.

---

### Task 1: 설정·라우팅·조립

**Files:**
- Create: `backend/app/providers/routing.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/providers/factory.py`
- Modify: `backend/app/main.py:31` (`get_provider(...)` 호출)
- Create: `backend/tests/test_routing.py`
- Modify: `backend/tests/test_config.py` (설정 검증 테스트 추가)

**Interfaces:**
- Produces:
  - `app.providers.routing.Effort` (Literal 타입), `ROUTABLE_STAGES: tuple[str, ...]`
  - `stage_targets(default_model: str, default_effort: str, stage_models: Mapping[str, str], stage_efforts: Mapping[str, str]) -> dict[str, tuple[str, str]]`
  - `class RoutedProvider(default: LLMProvider, routes: Mapping[str, LLMProvider])` — `name`, `complete(...)`
  - `get_provider(name, *, model=DEFAULT_CLAUDE_MODEL, effort=DEFAULT_CLAUDE_EFFORT, stage_models=None, stage_efforts=None) -> LLMProvider`

- [ ] **Step 1: 실패하는 테스트** (`backend/tests/test_routing.py`)

먼저 `tests/test_providers.py`(`test_get_provider_builds_claude_without_calling`이 키 환경 변수를 어떻게 다루는지)와 `tests/test_claude_provider.py`(`Server`, `provider_for`)를 읽고 같은 방식으로 쓴다. `LLMProvider` 프로토콜과 `ProviderResponse`는 `app/providers/base.py`에 있다.

```python
import anthropic
import httpx2 as httpx
import pytest
from pydantic import BaseModel

from app.providers.base import Prompt, ProviderResponse
from app.providers.claude import ClaudeProvider
from app.providers.factory import get_provider
from app.providers.mock import MockProvider
from app.providers.routing import ROUTABLE_STAGES, RoutedProvider, stage_targets

PROMPT = Prompt(system="고정", user="맥락")


def test_routable_stages_exclude_image():
    assert ROUTABLE_STAGES == ("diagnose", "easier_question", "propose_value", "generate", "validate")


def test_stage_targets_empty_settings_route_nothing():
    assert stage_targets("claude-opus-5-5", "medium", {}, {}) == {}


def test_stage_targets_fill_missing_half_with_default():
    targets = stage_targets(
        "claude-opus-5-5", "medium",
        {"diagnose": "claude-haiku-5-5", "generate": "claude-opus-5-5"},
        {"generate": "high", "validate": "medium"},
    )
    assert targets == {"diagnose": ("claude-haiku-5-5", "medium"), "generate": ("claude-opus-5-5", "high")}
    # validate는 기본과 같으므로 빠진다


class Recorder:
    def __init__(self, name):
        self.name, self.stages = name, []

    def complete(self, *, task_type, stage, prompt, response_model=None):
        self.stages.append(stage)
        return ProviderResponse(text="", model=self.name)


def test_routed_provider_sends_each_stage_to_its_provider():
    default, light = Recorder("default"), Recorder("light")
    routed = RoutedProvider(default, {"diagnose": light})
    routed.complete(task_type="branding", stage="diagnose", prompt=PROMPT)
    routed.complete(task_type="branding", stage="generate", prompt=PROMPT)
    assert light.stages == ["diagnose"] and default.stages == ["generate"]
    assert routed.name == "default"


@pytest.fixture
def fake_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


def test_mock_ignores_stage_settings():
    provider = get_provider("mock", stage_models={"diagnose": "claude-haiku-5-5"})
    assert isinstance(provider, MockProvider)


def test_claude_without_stage_settings_is_not_wrapped(fake_key):
    assert isinstance(get_provider("claude"), ClaudeProvider)


def test_claude_with_stage_settings_routes_and_shares_same_targets(fake_key):
    provider = get_provider(
        "claude",
        model="claude-opus-5-5", effort="medium",
        stage_models={"diagnose": "claude-haiku-5-5", "easier_question": "claude-haiku-5-5"},
        stage_efforts={"generate": "high"},
    )
    assert isinstance(provider, RoutedProvider)
    routes = provider.routes
    assert routes["diagnose"] is routes["easier_question"]
    assert (routes["diagnose"].model, routes["diagnose"].effort) == ("claude-haiku-5-5", "medium")
    assert (routes["generate"].model, routes["generate"].effort) == ("claude-opus-5-5", "high")
    assert (provider.default.model, provider.default.effort) == ("claude-opus-5-5", "medium")


class Answer(BaseModel):
    text: str


def test_routed_requests_carry_stage_model_and_effort():
    """실제 SDK 클라이언트 + MockTransport로 요청 본문을 본다(네트워크·비용 없음)."""
    import json

    bodies = []

    def server(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(200, json={
            "id": "msg", "type": "message", "role": "assistant", "model": bodies[-1]["model"],
            "content": [{"type": "text", "text": '{"text": "ok"}'}],
            "stop_reason": "end_turn", "stop_sequence": None,
            "usage": {"input_tokens": 1, "output_tokens": 1},
        })

    def claude(model, effort):
        client = anthropic.Anthropic(api_key="test-key", http_client=httpx.Client(transport=httpx.MockTransport(server)), max_retries=0)
        return ClaudeProvider(model=model, effort=effort, client=client)

    routed = RoutedProvider(claude("claude-opus-5-5", "medium"), {"diagnose": claude("claude-haiku-5-5", "low")})
    routed.complete(task_type="branding", stage="diagnose", prompt=PROMPT, response_model=Answer)
    routed.complete(task_type="branding", stage="generate", prompt=PROMPT, response_model=Answer)
    haiku, opus = bodies
    assert (haiku["model"], haiku["output_config"]["effort"]) == ("claude-haiku-5-5", "low")
    assert "fallbacks" not in haiku
    assert (opus["model"], opus["output_config"]["effort"]) == ("claude-opus-5-5", "medium")
    assert opus["fallbacks"] == "default"
```

`ClaudeProvider` 응답 처리가 `model`을 무엇으로 채우는지, `fallbacks` 키 이름이 본문에 어떻게 실리는지는 `tests/test_claude_provider.py`의 기존 단정과 맞춘다(다르면 그쪽 방식이 맞다).

설정 검증 테스트(`backend/tests/test_config.py`에 덧붙임, 기존 테스트처럼 `Settings(_env_file=None, ...)`):

```python
import pytest
from pydantic import ValidationError


def test_stage_settings_default_empty():
    settings = Settings(_env_file=None)
    assert settings.claude_stage_models == {} and settings.claude_stage_efforts == {}


def test_stage_settings_read_json_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_STAGE_MODELS", '{"diagnose": "claude-haiku-5-5"}')
    monkeypatch.setenv("CLAUDE_STAGE_EFFORTS", '{"generate": "high"}')
    settings = Settings(_env_file=None)
    assert settings.claude_stage_models == {"diagnose": "claude-haiku-5-5"}
    assert settings.claude_stage_efforts == {"generate": "high"}


@pytest.mark.parametrize("bad", [{"generat": "claude-haiku-5-5"}, {"image": "claude-haiku-5-5"}])
def test_unknown_stage_names_are_rejected(bad):
    with pytest.raises(ValidationError, match="diagnose"):  # 메시지에 허용 단계 이름이 있다
        Settings(_env_file=None, claude_stage_models=bad)


def test_bad_effort_is_rejected():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, claude_stage_efforts={"generate": "ultra"})
    with pytest.raises(ValidationError):
        Settings(_env_file=None, claude_stage_efforts={"imagee": "low"})
```

- [ ] **Step 2: 실패 확인** — `uv run --directory backend pytest tests/test_routing.py tests/test_config.py -q` → ImportError·실패.

- [ ] **Step 3: `backend/app/providers/routing.py`**

```python
"""단계별 모델 라우팅. 하네스는 그대로 단계 이름을 넘기고, 어느 모델이 답할지는 여기서 정한다.

설정이 없으면 쓰지 않는다(factory가 감싸지 않는다). 고르기는 순수 함수, RoutedProvider는 넘기기만 한다.
로드맵: docs/HARNESS-ROADMAP.md 3장.
"""
from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

from app.harness.prompting import STAGES
from app.providers.base import LLMProvider, Prompt, ProviderResponse

Effort = Literal["low", "medium", "high", "xhigh", "max"]
ROUTABLE_STAGES = tuple(stage for stage in STAGES if stage != "image")  # 이미지는 ImageProvider가 맡는다


def stage_targets(
    default_model: str,
    default_effort: str,
    stage_models: Mapping[str, str],
    stage_efforts: Mapping[str, str],
) -> dict[str, tuple[str, str]]:
    """[순수] 설정에 나온 단계마다 (모델, 노력). 정하지 않은 쪽은 기본값, 결과가 기본과 같으면 뺀다."""
    targets: dict[str, tuple[str, str]] = {}
    for stage in ROUTABLE_STAGES:
        if stage not in stage_models and stage not in stage_efforts:
            continue
        target = (stage_models.get(stage, default_model), stage_efforts.get(stage, default_effort))
        if target != (default_model, default_effort):
            targets[stage] = target
    return targets


class RoutedProvider:
    """단계 이름으로 제공자를 골라 그대로 넘긴다. 정하지 않은 단계는 기본 제공자."""

    def __init__(self, default: LLMProvider, routes: Mapping[str, LLMProvider]) -> None:
        self.default = default
        self.routes = dict(routes)
        self.name = default.name  # trace의 provider. 실제 모델 id는 응답의 model로 남는다

    def complete(
        self, *, task_type: str, stage: str, prompt: Prompt, response_model: type[BaseModel] | None = None
    ) -> ProviderResponse:
        provider = self.routes.get(stage, self.default)
        return provider.complete(task_type=task_type, stage=stage, prompt=prompt, response_model=response_model)
```

`app.harness.prompting`을 import할 때 순환 import가 나면(`config.py` → `routing.py` → `prompting` → …), `ROUTABLE_STAGES`를 `prompting.STAGES`와 같은 값의 튜플로 직접 적고 `tests/test_routing.py`에 `assert set(ROUTABLE_STAGES) == set(STAGES) - {"image"}` 테스트를 더해 둘이 어긋나지 않게 묶는다.

- [ ] **Step 4: 설정** (`backend/app/config.py`)

```python
from pydantic import field_validator

from app.providers.routing import ROUTABLE_STAGES, Effort
...
    claude_effort: Effort = "medium"  # 생각 깊이·비용
    # 단계별 라우팅(기본 꺼짐). JSON 객체. 예: CLAUDE_STAGE_MODELS={"diagnose":"claude-haiku-5-5"}
    claude_stage_models: dict[str, str] = {}
    claude_stage_efforts: dict[str, Effort] = {}
...
    @field_validator("claude_stage_models", "claude_stage_efforts")
    @classmethod
    def _known_stages(cls, value: dict[str, str]) -> dict[str, str]:
        unknown = sorted(set(value) - set(ROUTABLE_STAGES))
        if unknown:
            raise ValueError(
                f"라우팅할 수 없는 단계입니다: {', '.join(unknown)} (가능: {', '.join(ROUTABLE_STAGES)})"
            )
        return value
```

기존 `Literal[...]` import가 쓰이지 않게 되면 지운다.

- [ ] **Step 5: 조립** (`backend/app/providers/factory.py`)

```python
from collections.abc import Mapping

from app.providers.base import LLMProvider
from app.providers.mock import MockProvider
from app.providers.routing import RoutedProvider, stage_targets
...
def get_provider(
    name: str,
    *,
    model: str = DEFAULT_CLAUDE_MODEL,
    effort: str = DEFAULT_CLAUDE_EFFORT,
    stage_models: Mapping[str, str] | None = None,
    stage_efforts: Mapping[str, str] | None = None,
) -> LLMProvider:
    if name == "mock":
        return MockProvider()  # 비용 0. 단계 설정은 보지 않는다
    if name == "claude":
        from app.providers.claude import ClaudeProvider  # mock만 쓸 때는 SDK를 읽지 않는다

        default = ClaudeProvider(model=model, effort=effort)
        targets = stage_targets(model, effort, stage_models or {}, stage_efforts or {})
        if not targets:
            return default
        built: dict[tuple[str, str], LLMProvider] = {(model, effort): default}
        for target in targets.values():
            if target not in built:
                built[target] = ClaudeProvider(model=target[0], effort=target[1])
        return RoutedProvider(default, {stage: built[target] for stage, target in targets.items()})
    raise ValueError(...)  # 기존 문구 그대로
```

`backend/app/main.py`의 호출에 `stage_models=settings.claude_stage_models, stage_efforts=settings.claude_stage_efforts`를 더한다.

- [ ] **Step 6: 통과 확인** — `uv run --directory backend pytest -q` → 전부 통과.

- [ ] **Step 7: 커밋**

```bash
git add backend/app backend/tests
git commit -m "단계별 모델 라우팅: CLAUDE_STAGE_MODELS·CLAUDE_STAGE_EFFORTS(기본 꺼짐), RoutedProvider"
```

---

### Task 2: 문서 — 인수 기업 안내·로드맵·설정 예시

**Files:**
- Modify: `backend/.env.example`
- Modify: `docs/HARNESS-ROADMAP.md` (2장 끝, 3장)
- Modify: `CLAUDE.md` (구조 절의 `backend/app/providers/` 줄, 비용 절)
- Modify: `README.md` (새 절 "인수 기업이 알아야 할 것")
- Modify: `docs/HANDOFF.md` (기준일·main·테스트 수·지금 상태 표·다음 할 일)
- Modify: `docs/WBS.xlsx` (`scripts/wbs.py`)

**Interfaces:**
- Consumes: Task 1의 설정 이름 `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`, `RoutedProvider`, `ROUTABLE_STAGES`.

- [ ] **Step 1: `.env.example`** — `# CLAUDE_EFFORT=...` 줄 바로 다음에 넣는다:

```
# 단계별 라우팅(기본 꺼짐, JSON). 단계: diagnose, easier_question, propose_value, generate, validate
# 측정(docs/HARNESS-ROADMAP.md 0단계) 전에는 켜지 않는다. 예: 가벼운 단계는 Haiku, 생성은 노력 높이기
# CLAUDE_STAGE_MODELS={"diagnose":"claude-haiku-5-5","easier_question":"claude-haiku-5-5","propose_value":"claude-haiku-5-5"}
# CLAUDE_STAGE_EFFORTS={"generate":"high"}
```

- [ ] **Step 2: 로드맵** (`docs/HARNESS-ROADMAP.md`)
  - 2장 "하네스 때문인지 가르는 실험" 문단 뒤에 한 문단: "**여러 모델로 나누기 전에** 같은 모델에서 단계별 노력만 낮춘 경우(`CLAUDE_STAGE_EFFORTS`)를 먼저 잰다. 최신 모델은 낮은 노력으로도 이전 세대의 높은 노력에 맞먹는 경우가 많고, 모델 하나면 운영이 단순하다."
  - 3장 제목을 "## 3. 1단계 — 단계별 모델 라우팅 (구현됨, task/26)"으로 바꾸고 "조절 손잡이" 줄을 다음으로 바꾼다: "- **조절 손잡이:** `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`(JSON, 단계 → 모델·노력, `backend/.env.example`). 기본은 비어 있어 모든 단계가 `CLAUDE_MODEL`·`CLAUDE_EFFORT`를 쓴다. 없는 단계 이름·잘못된 노력 값은 서버 시작 때 실패한다. 구현: `app/providers/routing.py`(`stage_targets`, `RoutedProvider`)."
  - 6장 표의 1단계 행 "지금" 칸을 "구현됨(기본 꺼짐)"으로.

- [ ] **Step 3: CLAUDE.md**
  - 구조 절 `backend/app/providers/` 줄 끝(이미지 문장 앞이나 뒤)에: "단계별 모델 라우팅은 `routing.py`(`RoutedProvider`, 설정 `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`, 기본 꺼짐, Mock이면 쓰지 않는다)."
  - 비용 절 끝에: "단계마다 다른 모델·노력은 `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`로 정한다(측정 전에는 켜지 않는다, `docs/HARNESS-ROADMAP.md`)."

- [ ] **Step 4: README — "인수 기업이 알아야 할 것" 절**

`README.md`의 "## 남은 일 — 팀에서 상의할 것" 절 바로 뒤(진행 현황 문장 다음)에 아래 절을 그대로 넣는다. 각 항목의 파일·설정 이름이 실제 저장소와 맞는지 확인하고, 다르면 실제 이름으로 고친다.

```markdown
## 인수 기업이 알아야 할 것

프로토타입은 비용 0으로 만들었다. 실제로 운영하려면 아래를 정하고 바꾼다. 자세한 절차는 링크한 문서에 있다.

| 무엇 | 지금 | 바꾸는 법 | 문서 |
|---|---|---|---|
| **계정·키** | 배포(버셀·렌더)와 API 키가 개발자 개인 것 | 인수 기업 계정으로 다시 배포하고 개인 키는 폐기 | [`docs/HANDOFF.md`](docs/HANDOFF.md) "개인 계정·키·로컬 데이터", [`docs/DEPLOY.md`](docs/DEPLOY.md) |
| **실제 AI 호출** | Mock(`PROVIDER=mock`) | `PROVIDER=claude` + 환경 변수 `ANTHROPIC_API_KEY`, 모델 `CLAUDE_MODEL`·노력 `CLAUDE_EFFORT`. 먼저 `scripts/claude_smoke.py`로 확인 | [`backend/.env.example`](backend/.env.example) |
| **품질부터 잰다** | 실제 모델로 잰 적 없음 | 과제별 평가 시나리오(`evals/`)를 실제 모델로 돌려 형식 실패·거절·규칙 위반·품질·비용을 잰 뒤에 튜닝·아키텍처를 정한다 | [`docs/HARNESS-ROADMAP.md`](docs/HARNESS-ROADMAP.md) 0단계 |
| **단계별 모델 라우팅** | 구현됨, 기본 꺼짐 | `CLAUDE_STAGE_MODELS`·`CLAUDE_STAGE_EFFORTS`(JSON). 측정 뒤 약한 단계만 올리거나 가벼운 단계를 싸게 | 로드맵 1단계 |
| **디코딩 제약·LoRA** | 하지 않음(Claude API로는 불가) | 오픈 가중치 모델 서버를 붙일 때 `app/providers/`에 제공자를 더한다. 조건은 로드맵에 | 로드맵 2·3단계 |
| **과제 하네스 튜닝** | 과제 폴더마다 정책·프롬프트·검증·시나리오 | `backend/app/harness/tasks/<과제>/`만 고친다. 고친 뒤 `uv run --directory backend pytest` | [`CLAUDE.md`](CLAUDE.md) "과제 하네스를 고칠 때" |
| **외부 전송 보호** | 개인정보 자동 가림, 비공개 항목, 고지 동의, 프롬프트 주입 기본 방어 | 고지문을 바꾸면 `NOTICE_VERSION`을 올린다. AI 업체와 데이터 보관·학습 계약, 개인정보 처리방침은 인수 기업이 정한다 | HANDOFF "남겨 둔 것·알려진 한계" |
| **데이터 보관** | 무료 렌더라 다시 시작하면 지워짐, SQLite 평문 | 유료 디스크 또는 DB, 저장 시 암호화(키 관리), 로그인 뒤 보관 기간·삭제 | [`docs/DEPLOY.md`](docs/DEPLOY.md) "나중에 바꿀 것" |
| **로그인** | 브라우저 익명 ID(`X-Client-Id`) | `backend/app/api/owner.py`의 `current_owner` 하나만 바꾼다 | CLAUDE.md 하네스 원칙 |
| **이미지·웹 검색** | 자리표시 이미지, 근거 자료 샘플 | `ImageProvider`(`app/providers/image.py`), `find_evidence` 단계만 바꾼다 | CLAUDE.md |
| **비용 습관** | 테스트는 늘 Mock | 실제 호출 테스트는 따로 돌리고, `llm_validation`(생성마다 호출 하나 더)은 필요할 때만 켠다 | CLAUDE.md "비용" |
```

- [ ] **Step 5: HANDOFF·WBS**
  - `docs/HANDOFF.md`: 기준일 2026-10-19, main `a6ca0fa` (PR #25까지 머지), 테스트 수(Task 1 결과), "지금 상태" 표에 기존 형식대로 `단계별 모델 라우팅(기본 꺼짐) | #26`과 `하네스 성능 로드맵·인수 안내(README) | #26` 행, "다음 할 일"에 "인수 팀: 로드맵 0단계 측정 → 라우팅 설정" 한 줄(이미 비슷한 줄이 있으면 고친다).
  - WBS: `PYTHONIOENCODING=utf-8 uv run --no-project --with openpyxl python scripts/wbs.py list`로 6.5 행 형식을 보고, `scripts/wbs.py --help`로 인자를 확인해 6.6 "단계별 모델 라우팅·하네스 로드맵·인수 안내" 행을 `add`, `set`으로 `완료`·완료일 2026-10-19·진척률 1·PR 26, `date 2026-10-19`. 파일이 엑셀에 열려 있어 PermissionError가 나면 멈추고 알린다.

- [ ] **Step 6: 확인과 커밋** — `uv run --directory backend pytest -q` 통과(문서만 바뀌었지만 `.env.example`을 읽는 테스트가 있으면 확인).

```bash
git add backend/.env.example docs/HARNESS-ROADMAP.md CLAUDE.md README.md docs/HANDOFF.md docs/WBS.xlsx
git commit -m "문서: 인수 기업 안내(README), 라우팅 설정 예시, 로드맵·HANDOFF·WBS"
```
