# AX 코칭 플랫폼 개발 기반(Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 과제별 하네스를 독립적으로 튜닝할 수 있는 FastAPI 백엔드 골격, Mock 기반 개발 루프, 계약을 공유하는 최소 React 프론트를 만든다.

**Architecture:** 공통 `BaseHarness`가 단계(진단 → 질문 선택 → 답변 반영 → 준비도·종료 → 생성 → 검증)를 메서드 단위로 실행하고, 과제 폴더(`tasks/<task>/`)가 결과물 스키마·정책 YAML·프롬프트·검증 규칙·시나리오를 소유한다. 모든 LLM 호출은 `LLMProvider` 인터페이스를 거치며 지금은 `MockProvider`(JSON Schema 자동 채움)만 있다. API 계약의 원본은 백엔드 Pydantic 모델이고, 프론트 타입은 OpenAPI에서 생성한다.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2, pydantic-settings, PyYAML, Jinja2, pytest / React, Vite, TypeScript, openapi-typescript, openapi-fetch

**Spec:** `docs/superpowers/specs/2026-10-15-ax-platform-foundation-design.md`

## Global Constraints

- Python `>=3.12`, 패키지·실행은 `uv`. 프론트는 Node 24 + npm.
- 모든 명령은 저장소 루트(`D:\ax_platform_5\ax_platform_5`)에서 실행한다. 백엔드는 `uv run --directory backend ...`, 프론트는 `npm --prefix frontend ...`.
- 비용 0: 테스트와 개발 루프는 `MockProvider`만 쓴다. 실제 LLM API 호출 코드는 만들지 않는다.
- API 계약의 원본은 `backend/app/schemas/`와 `backend/app/core/`의 Pydantic 모델이다. `frontend/src/api/schema.d.ts`는 생성물이며 손으로 고치지 않는다.
- 시스템 프롬프트와 정책 YAML 내용은 API 응답으로 내보내지 않는다.
- 사용자에게 보이는 문구·주석·docstring은 한국어, 코드 식별자는 영어.
- 질문 모드 상한 기본값: quick 3 / standard 5 / precise 10. `max_easier_level` 기본 4.
- 커밋·PR: Task마다 최신 `main`에서 `task/<N>-<이름>` 브랜치를 따서 커밋하고, 푸시 후 PR을 올린다. 머지는 사용자가 직접 하며, 머지 전에는 다음 Task를 시작하지 않는다. `.gitignore`, `README.md`, `docs/superpowers/`는 저장소 초기 커밋에 이미 들어 있다. 커밋 메시지에 Co-Authored-By 등 AI 귀속 줄을 넣지 않는다.
- 개발 방식: 모든 구현은 TDD(실패하는 테스트 확인 → 최소 구현 → 통과 확인)로 한다.

## File Structure

```
.gitignore
CLAUDE.md                                   # Task 9
design/README.md                            # Task 1 — 디자인 HTML 수령 절차
docs/planning/                              # Task 1 — 기획 PDF 사본 + 추출 텍스트
backend/
  pyproject.toml, .env.example              # Task 1
  app/main.py                               # Task 7 — create_app(), 예외 처리
  app/config.py                             # Task 1 — Settings(provider, debug)
  app/core/results.py                       # Task 1 — 결과·검증 모델 (과제 공통 래퍼)
  app/core/state.py                         # Task 1 — 세션 상태 모델
  app/core/store.py                         # Task 1 — SessionStore + 메모리 구현
  app/providers/base.py                     # Task 2 — LLMProvider 인터페이스, 오류
  app/providers/mock_fill.py                # Task 2 — JSON Schema 기반 Mock 값 채우기
  app/providers/mock.py                     # Task 2 — MockProvider
  app/providers/factory.py                  # Task 2 — get_provider()
  app/harness/policy.py                     # Task 3 — policy.yaml 모델·로더
  app/harness/prompting.py                  # Task 3 — 템플릿 렌더러 (과제 우선 → 공통)
  app/harness/prompts/*.md                  # Task 3 — 공통 프롬프트
  app/harness/errors.py                     # Task 4 — HarnessError 등
  app/harness/stage_models.py               # Task 4 — LLM 단계 응답 모델
  app/harness/base.py                       # Task 4(질문) + Task 5(생성·검증)
  app/harness/validation.py                 # Task 5 — 공통 검증 규칙
  app/harness/evals.py                      # Task 5 — 시나리오 실행기
  app/harness/registry.py                   # Task 6 — 과제 등록
  app/harness/tasks/<task>/...              # Task 6 — 과제 4개
  app/schemas/coaching.py                   # Task 7 — API 요청·응답
  app/api/deps.py, views.py, coaching.py    # Task 7 — 라우터
  scripts/export_openapi.py                 # Task 7
  tests/...                                 # 각 Task
frontend/                                   # Task 8
```

---

### Task 1: 저장소 기반과 세션 상태 모델

**Files:**
- Create: `.gitignore`, `design/README.md`, `docs/planning/` (PDF 사본·텍스트)
- Create: `backend/pyproject.toml`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`
- Create: `backend/app/core/__init__.py`, `backend/app/core/results.py`, `backend/app/core/state.py`, `backend/app/core/store.py`
- Test: `backend/tests/test_state.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `app.core.results`: `utcnow() -> datetime`, `CardType`, `ResultCard`, `ResultAssumption`, `TaskResult[ContentT]`(cards, assumptions, full_text, content), `GenerationResult`(cards, assumptions, full_text, content: dict, generated_at), `ValidationIssue`(rule, message, severity: "warning"|"error"), `ValidationReport`(issues, passed)
  - `app.core.state`: `SessionStatus`, `CoachingMode`, `InfoSource`, `AnswerType`, `InfoItem`, `Assumption`, `Conflict`, `QuestionOption`(id, label, ai_suggested), `Question`(question_id, field, text, options, multi_select, level, is_ai_proposal), `Answer`(question_id, answer_type, value, option_ids), `AskedQuestion`(question, answer_type, value, answered_at), `TraceEntry`, `HarnessProfile`, `SessionState`(+ `find_asked(question_id)`)
  - `app.core.store`: `SessionStore` 프로토콜(`get(session_id) -> SessionState | None`, `save(state) -> None`), `InMemorySessionStore`
  - `app.config`: `settings: Settings`(provider: str = "mock", debug: bool = True)

- [ ] **Step 1: 브랜치·폴더 준비와 기획 문서 사본**

```bash
git switch -c feat/foundation
mkdir -p backend/app/core backend/tests docs/planning design
cp "../AX Coaching Platform 기능 설계.pdf" "../AX_코칭_플랫폼_기획_및_하네스_설계서.pdf" docs/planning/
pdftotext -layout -enc UTF-8 "docs/planning/AX Coaching Platform 기능 설계.pdf" "docs/planning/AX Coaching Platform 기능 설계.txt"
pdftotext -layout -enc UTF-8 "docs/planning/AX_코칭_플랫폼_기획_및_하네스_설계서.pdf" "docs/planning/AX_코칭_플랫폼_기획_및_하네스_설계서.txt"
```

(Bash 도구로 실행. 브랜치 전환은 사용자가 커밋을 승인한 경우에만.)

- [ ] **Step 2: `.gitignore`와 `design/README.md` 작성**

`.gitignore`:
```gitignore
# Python
__pycache__/
*.pyc
.venv/
.pytest_cache/
backend/.env

# Node
node_modules/
frontend/dist/
frontend/openapi.json

# OS / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

`design/README.md`:
```markdown
# 디자인 HTML 원본

디자인 팀원이 피그마에서 내보낸 프로토타입 HTML을 **받은 그대로** 보관한다. 이 폴더의 파일은 고치지 않는다.

## 새 디자인을 받았을 때

1. `design/YYYY-MM-DD[-설명]/` 폴더를 만들고 HTML과 에셋을 그대로 넣는다.
2. 직전 버전과 비교한다: `git diff --no-index design/<이전 폴더> design/<새 폴더>`
3. 화면·상태(설계서 9.3: 초기·정보 부족·생성 중·완료·실패·수정)를 대조해 API가 바뀌어야 하는지 먼저 정리한다.
4. API가 바뀌면 백엔드 `app/schemas/`를 고치고 `npm --prefix frontend run gen:api`로 프론트 타입을 다시 만든다.
5. React 컴포넌트에 바뀐 화면만 반영한다.
```

- [ ] **Step 3: 백엔드 프로젝트와 의존성**

`backend/pyproject.toml`:
```toml
[project]
name = "ax-coaching-backend"
version = "0.1.0"
description = "AX 코칭 플랫폼 백엔드"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Run:
```bash
uv add --directory backend "fastapi[standard]" pydantic-settings pyyaml jinja2
uv add --directory backend --dev pytest
```
Expected: `backend/uv.lock` 생성, `pyproject.toml`의 dependencies가 채워짐.

`backend/.env.example`:
```dotenv
# 모델 제공자. 지금은 mock만 지원한다.
PROVIDER=mock
# true면 /sessions/{id}/trace 디버깅 엔드포인트를 연다.
DEBUG=true
```

`backend/app/__init__.py`, `backend/app/core/__init__.py`: 빈 파일.

`backend/app/config.py`:
```python
"""환경 설정. backend/.env 또는 환경 변수에서 읽는다."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    provider: str = "mock"
    debug: bool = True


settings = Settings()
```

- [ ] **Step 4: 실패하는 테스트 작성**

`backend/tests/test_state.py`:
```python
from app.core.results import ValidationIssue, ValidationReport
from app.core.state import CoachingMode, SessionState, SessionStatus
from app.core.store import InMemorySessionStore


def test_new_session_defaults():
    state = SessionState(task_type="product_planning")
    assert state.session_id.startswith("sess_")
    assert state.mode is CoachingMode.STANDARD
    assert state.status is SessionStatus.DRAFTING
    assert state.facts == {}
    assert state.trace == []
    assert state.pending_question is None


def test_store_returns_independent_copies():
    store = InMemorySessionStore()
    state = SessionState(task_type="branding")
    store.save(state)

    loaded = store.get(state.session_id)
    loaded.raw_input = "바뀐 값"

    assert store.get(state.session_id).raw_input == ""


def test_store_missing_session_returns_none():
    assert InMemorySessionStore().get("sess_없음") is None


def test_validation_report_passes_only_without_errors():
    warning = ValidationIssue(rule="r", message="m")
    error = ValidationIssue(rule="r", message="m", severity="error")
    assert ValidationReport(issues=[warning]).passed
    assert not ValidationReport(issues=[warning, error]).passed
```

- [ ] **Step 5: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.results'`

- [ ] **Step 6: 결과·상태·저장소 구현**

`backend/app/core/results.py`:
```python
"""생성 결과와 검증 리포트. 모든 과제가 공유하는 결과 래퍼다."""
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, computed_field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CardType(StrEnum):
    DIAGNOSIS = "diagnosis"
    SUGGESTION = "suggestion"
    ACTION = "action"


class ResultCard(BaseModel):
    card_type: CardType = Field(description="카드 유형: 진단·제안·실행 과제")
    title: str = Field(description="카드 제목")
    body: str = Field(description="카드 본문")
    order: int = Field(description="표시 순서")


class ResultAssumption(BaseModel):
    field: str = Field(description="AI가 보완한 항목의 필드 이름")
    value: str = Field(description="AI가 가정한 값")
    requires_confirmation: bool = Field(default=True, description="사용자 확인이 필요한지")


ContentT = TypeVar("ContentT", bound=BaseModel)


class TaskResult(BaseModel, Generic[ContentT]):
    """LLM이 채워야 하는 결과 형태. content 자리에 과제별 output_schema가 들어간다."""

    cards: list[ResultCard] = Field(description="모바일 결과 카드 목록")
    assumptions: list[ResultAssumption] = Field(
        default_factory=list, description="AI가 가정으로 보완한 항목"
    )
    full_text: str = Field(description="복사·저장용 완성본")
    content: ContentT


class GenerationResult(BaseModel):
    """세션에 저장되는 결과. content는 과제별 스키마를 통과한 값의 dict다."""

    cards: list[ResultCard]
    assumptions: list[ResultAssumption] = Field(default_factory=list)
    full_text: str
    content: dict[str, Any]
    generated_at: datetime = Field(default_factory=utcnow)


class ValidationIssue(BaseModel):
    rule: str = Field(description="어긴 규칙 이름")
    message: str = Field(description="사용자·개발자가 읽을 설명")
    severity: Literal["warning", "error"] = Field(default="warning", description="심각도")


class ValidationReport(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list)

    @computed_field
    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)
```

`backend/app/core/state.py`:
```python
"""세션 상태. 설계서 10.2(세션 상태)와 12장(사실·가정 분리)을 그대로 옮긴 모델이다."""
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.results import GenerationResult, ValidationReport, utcnow


class SessionStatus(StrEnum):
    DRAFTING = "drafting"
    CLARIFYING = "clarifying"
    CONFIRMING = "confirming"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISING = "revising"


class CoachingMode(StrEnum):
    QUICK = "quick"
    STANDARD = "standard"
    PRECISE = "precise"


class InfoSource(StrEnum):
    USER_FREE_TEXT = "user_free_text"
    USER_SELECTED_AI_OPTION = "user_selected_ai_option"
    PREVIOUS_TASK = "previous_task"
    AI_ASSUMPTION = "ai_assumption"
    DEFAULT = "default"


class AnswerType(StrEnum):
    OPTION = "option"
    FREE_TEXT = "free_text"
    DONT_KNOW = "dont_know"
    SKIP = "skip"


class InfoItem(BaseModel):
    value: str
    source: InfoSource
    confidence: float = 1.0
    updated_at: datetime = Field(default_factory=utcnow)


class Assumption(InfoItem):
    reason: str = ""
    requires_confirmation: bool = True


class Conflict(BaseModel):
    field: str
    values: list[str]


class QuestionOption(BaseModel):
    id: str
    label: str
    ai_suggested: bool = False


class Question(BaseModel):
    question_id: str = Field(default_factory=lambda: f"q_{uuid4().hex[:10]}")
    field: str
    text: str
    options: list[QuestionOption] = Field(default_factory=list)
    multi_select: bool = False
    level: int = 0  # 0 = 기본 질문, 1 이상 = '모르겠어요' 사다리 단계
    is_ai_proposal: bool = False


class Answer(BaseModel):
    question_id: str
    answer_type: AnswerType
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class AskedQuestion(BaseModel):
    question: Question
    answer_type: AnswerType | None = None
    value: str | None = None
    answered_at: datetime | None = None


class TraceEntry(BaseModel):
    stage: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    usage: dict[str, int] = Field(default_factory=dict)
    at: datetime = Field(default_factory=utcnow)


class HarnessProfile(BaseModel):
    """설계서 6.4 하네스 설정값. 지금은 기본값만 쓰고, 온보딩 설문(ON)이 생기면 채운다."""

    prompt_skill: str = "beginner"
    coaching_style: str = "step_by_step"
    preferred_detail: str = "medium"
    feedback_tone: str = "balanced"
    result_format: str = "mobile_cards"
    alternative_count: int = 3
    assumption_policy: str = "ask_first"
    question_batch_size: int = 1
    use_examples: bool = True


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:12]}")
    task_type: str
    mode: CoachingMode = CoachingMode.STANDARD
    status: SessionStatus = SessionStatus.DRAFTING
    profile: HarnessProfile = Field(default_factory=HarnessProfile)
    raw_input: str = ""
    facts: dict[str, InfoItem] = Field(default_factory=dict)
    assumptions: dict[str, Assumption] = Field(default_factory=dict)
    unknowns: list[str] = Field(default_factory=list)
    dont_know_levels: dict[str, int] = Field(default_factory=dict)  # 모르겠어요 사다리 현재 단계
    conflicts: list[Conflict] = Field(default_factory=list)
    asked_questions: list[AskedQuestion] = Field(default_factory=list)
    pending_question: Question | None = None
    readiness: float = 0.0
    result: GenerationResult | None = None
    result_stale: bool = False
    validation: ValidationReport | None = None
    error: str | None = None
    trace: list[TraceEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def find_asked(self, question_id: str) -> AskedQuestion | None:
        return next(
            (a for a in self.asked_questions if a.question.question_id == question_id), None
        )
```

`backend/app/core/store.py`:
```python
"""세션 저장소. 지금은 메모리 구현만 있다."""
from typing import Protocol

from app.core.results import utcnow
from app.core.state import SessionState


class SessionStore(Protocol):
    def get(self, session_id: str) -> SessionState | None: ...

    def save(self, state: SessionState) -> None: ...


class InMemorySessionStore:
    """서버를 재시작하면 사라진다. 영속화가 필요해지면 같은 인터페이스로 SQLite 구현을 추가한다."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState | None:
        state = self._sessions.get(session_id)
        return state.model_copy(deep=True) if state else None

    def save(self, state: SessionState) -> None:
        state.updated_at = utcnow()
        self._sessions[state.session_id] = state.model_copy(deep=True)
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_state.py -v`
Expected: 4 passed

- [ ] **Step 8: Commit**

```bash
git add .gitignore design/README.md docs/planning docs/superpowers backend
git commit -m "chore: 저장소 기반과 세션 상태 모델 추가"
```

---

### Task 2: LLM Provider 인터페이스와 MockProvider

**Files:**
- Create: `backend/app/providers/__init__.py`(빈 파일), `backend/app/providers/base.py`, `backend/app/providers/mock_fill.py`, `backend/app/providers/mock.py`, `backend/app/providers/factory.py`
- Test: `backend/tests/test_providers.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `app.providers.base`: `Usage`(input_tokens, output_tokens), `ProviderResponse`(text, model, parsed, usage), `ProviderError`, `ProviderOutputError(ProviderError)`, `LLMProvider` 프로토콜 `complete(*, task_type: str, stage: str, prompt: str, response_model: type[BaseModel] | None = None) -> ProviderResponse`, 속성 `name: str`
  - `app.providers.mock_fill`: `mock_instance(model: type[BaseModel]) -> BaseModel`
  - `app.providers.mock`: `MockProvider(fail_stages: set[str] | None = None, output_errors: dict[str, int] | None = None)`, 속성 `calls: list[tuple[str, str]]`
  - `app.providers.factory`: `get_provider(name: str) -> LLMProvider`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_providers.py`:
```python
from enum import StrEnum

import pytest
from pydantic import BaseModel, Field

from app.providers.base import ProviderError, ProviderOutputError
from app.providers.factory import get_provider
from app.providers.mock import MockProvider
from app.providers.mock_fill import mock_instance


class Kind(StrEnum):
    FIRST = "first"
    SECOND = "second"


class Inner(BaseModel):
    title: str = Field(description="제목")
    score: int


class Outer(BaseModel):
    name: str
    tags: list[str]
    inner: Inner
    items: list[Inner]
    kind: Kind
    note: str | None = None
    flag: bool


def test_mock_instance_fills_nested_schema():
    obj = mock_instance(Outer)
    assert obj.inner.title == "[mock] 제목"
    assert len(obj.items) == 1
    assert obj.kind is Kind.FIRST
    assert obj.tags and obj.tags[0].startswith("[mock]")
    assert obj.note is not None and obj.note.startswith("[mock]")


def test_mock_provider_returns_parsed_and_records_call():
    provider = MockProvider()
    response = provider.complete(task_type="t", stage="generate", prompt="hello", response_model=Inner)
    assert isinstance(response.parsed, Inner)
    assert response.model == "mock"
    assert response.usage.input_tokens == 5
    assert provider.calls == [("t", "generate")]


def test_mock_provider_without_model_returns_text():
    response = MockProvider().complete(task_type="t", stage="diagnose", prompt="p")
    assert response.parsed is None
    assert response.text == "[mock] diagnose"


def test_mock_provider_failure_modes():
    with pytest.raises(ProviderError):
        MockProvider(fail_stages={"generate"}).complete(task_type="t", stage="generate", prompt="p")

    provider = MockProvider(output_errors={"generate": 1})
    with pytest.raises(ProviderOutputError):
        provider.complete(task_type="t", stage="generate", prompt="p", response_model=Inner)
    assert provider.complete(task_type="t", stage="generate", prompt="p", response_model=Inner).parsed


def test_get_provider():
    assert get_provider("mock").name == "mock"
    with pytest.raises(ValueError):
        get_provider("claude")
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_providers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.providers'`

- [ ] **Step 3: Provider 구현**

`backend/app/providers/base.py`:
```python
"""모델 제공자 인터페이스. 하네스는 이 인터페이스만 알고 실제 모델은 모른다."""
from dataclasses import dataclass, field
from typing import Protocol

from pydantic import BaseModel


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ProviderResponse:
    text: str
    model: str
    parsed: BaseModel | None = None
    usage: Usage = field(default_factory=Usage)


class ProviderError(Exception):
    """모델 호출 자체가 실패했다 (네트워크, 인증, 한도 등)."""


class ProviderOutputError(ProviderError):
    """호출은 됐지만 응답이 요청한 스키마를 통과하지 못했다."""


class LLMProvider(Protocol):
    name: str

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse: ...
```

`backend/app/providers/mock_fill.py`:
```python
"""Pydantic 모델의 JSON Schema를 따라 Mock 값을 자동으로 채운다.

output_schema를 고쳐도 Mock을 따로 고치지 않아도 되게 하려는 장치다.
"""
from typing import Any

from pydantic import BaseModel


def mock_instance(model: type[BaseModel]) -> BaseModel:
    schema = model.model_json_schema()
    data = _fill(schema, schema.get("$defs", {}), model.__name__)
    return model.model_validate(data)


def _fill(schema: dict[str, Any], defs: dict[str, Any], name: str) -> Any:
    if "$ref" in schema:
        return _fill(defs[schema["$ref"].split("/")[-1]], defs, name)
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return schema["enum"][0]
    for key in ("anyOf", "oneOf"):
        if key in schema:
            options = [s for s in schema[key] if s.get("type") != "null"]
            return _fill(options[0], defs, name)
    if "allOf" in schema:
        return _fill(schema["allOf"][0], defs, name)

    kind = schema.get("type")
    label = schema.get("description") or name
    if kind == "object":
        properties = schema.get("properties", {})
        return {key: _fill(sub, defs, key) for key, sub in properties.items()}
    if kind == "array":
        count = max(schema.get("minItems", 1), 1)
        return [_fill(schema.get("items", {}), defs, name) for _ in range(count)]
    if kind == "integer":
        return 1
    if kind == "number":
        return 0.5
    if kind == "boolean":
        return True
    if schema.get("format") == "date-time":
        return "2026-01-01T00:00:00Z"
    return f"[mock] {label}"
```

`backend/app/providers/mock.py`:
```python
"""비용 0, 결정적인 Mock 제공자. 개발·테스트의 기본값이다."""
from pydantic import BaseModel

from app.providers.base import ProviderError, ProviderOutputError, ProviderResponse, Usage
from app.providers.mock_fill import mock_instance


class MockProvider:
    name = "mock"

    def __init__(
        self,
        fail_stages: set[str] | None = None,
        output_errors: dict[str, int] | None = None,
    ) -> None:
        # 테스트용: fail_stages의 단계는 항상 실패, output_errors는 단계별로 n번 스키마 오류를 낸다.
        self.fail_stages = fail_stages or set()
        self.output_errors = dict(output_errors or {})
        self.calls: list[tuple[str, str]] = []

    def complete(
        self,
        *,
        task_type: str,
        stage: str,
        prompt: str,
        response_model: type[BaseModel] | None = None,
    ) -> ProviderResponse:
        self.calls.append((task_type, stage))
        if stage in self.fail_stages:
            raise ProviderError(f"[mock] {stage} 단계 호출 실패")
        if self.output_errors.get(stage, 0) > 0:
            self.output_errors[stage] -= 1
            raise ProviderOutputError(f"[mock] {stage} 단계 응답이 스키마를 통과하지 못함")

        parsed = mock_instance(response_model) if response_model else None
        text = parsed.model_dump_json() if parsed else f"[mock] {stage}"
        return ProviderResponse(
            text=text,
            model="mock",
            parsed=parsed,
            usage=Usage(input_tokens=len(prompt), output_tokens=len(text)),
        )
```

`backend/app/providers/factory.py`:
```python
"""설정의 provider 이름으로 제공자를 만든다. 새 제공자는 여기에 한 줄씩 추가한다."""
from app.providers.base import LLMProvider
from app.providers.mock import MockProvider


def get_provider(name: str) -> LLMProvider:
    if name == "mock":
        return MockProvider()
    raise ValueError(f"지원하지 않는 provider입니다: {name} (현재 지원: mock)")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_providers.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/providers backend/tests/test_providers.py
git commit -m "feat: LLM Provider 인터페이스와 MockProvider 추가"
```

---

### Task 3: 과제 정책(policy.yaml) 로더와 프롬프트 렌더러

**Files:**
- Create: `backend/app/harness/__init__.py`(빈 파일), `backend/app/harness/policy.py`, `backend/app/harness/prompting.py`
- Create: `backend/app/harness/prompts/_context.md`, `_generate_base.md`, `diagnose.md`, `easier_question.md`, `propose_value.md`, `generate.md`, `validate.md`
- Create: `backend/tests/fixtures/sample_task/policy.yaml`, `backend/tests/fixtures/sample_task/prompts/generate.md`
- Test: `backend/tests/test_policy_prompting.py`

**Interfaces:**
- Consumes: `app.core.state.CoachingMode`, `SessionState`, `InfoItem`, `InfoSource`
- Produces:
  - `app.harness.policy`: `FieldKind`(MUST_CONFIRM, AI_SUGGEST, DEFAULT), `LadderStep`(question, options), `FieldPolicy`(name, label, kind, weight, question, options, multi_select, easier_questions, default), `TaskPolicy`(task_type, title, description, input_placeholder, input_examples, raw_input_field, readiness_threshold, question_caps, max_easier_level, llm_validation, fields, rules; `field(name) -> FieldPolicy`, `labels -> dict[str, str]`), `load_policy(path: Path) -> TaskPolicy`
  - `app.harness.prompting`: `STAGES`, `COMMON_PROMPTS_DIR`, `PromptRenderer(task_prompts_dir: Path)` + `render(stage: str, **context) -> str`
  - 템플릿 컨텍스트 규약: 항상 `state`, `policy`, `profile`. `easier_question`·`propose_value`는 `field`, `level`, `previous: list[str]`. `generate`는 `output_schema: str`. `validate`는 `result_text: str`.
  - 테스트 픽스처 `tests/fixtures/sample_task` (Task 4·5가 사용)

- [ ] **Step 1: 테스트 픽스처 작성**

`backend/tests/fixtures/sample_task/policy.yaml`:
```yaml
task_type: sample_task
title: 샘플 과제
description: 하네스 공통 로직 테스트용 과제
raw_input_field: idea
readiness_threshold: 0.8
question_caps: { quick: 2, standard: 3, precise: 5 }
max_easier_level: 4
fields:
  - name: idea
    label: 아이디어
    kind: must_confirm
    weight: 3
    question: 어떤 아이디어인가요?
  - name: customer
    label: 목표 고객
    kind: must_confirm
    weight: 3
    question: 누구를 위한 건가요?
    options: [20대 직장인, 부모, 학생]
    easier_questions:
      - question: 이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?
      - question: 둘 중 더 가까운 쪽을 골라 주세요.
        options: [나 자신, 다른 사람]
  - name: problem
    label: 고객 문제
    kind: must_confirm
    weight: 2
    question: 고객이 겪는 불편은 무엇인가요?
  - name: tone
    label: 톤
    kind: ai_suggest
    weight: 1
    question: 어떤 느낌이면 좋을까요?
    options: [따뜻한, 세련된, 유쾌한]
    multi_select: true
  - name: length
    label: 답변 길이
    kind: default
    weight: 1
    default: 중간
rules:
  - 근거 없는 숫자를 사실처럼 쓰지 않는다
```

`backend/tests/fixtures/sample_task/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
{% block task_guidance %}
## 샘플 과제 지침
샘플 지침 문구
{% endblock %}
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_policy_prompting.py`:
```python
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.core.state import CoachingMode, InfoItem, InfoSource, SessionState
from app.harness.policy import FieldKind, load_policy
from app.harness.prompting import STAGES, PromptRenderer

SAMPLE_DIR = Path(__file__).parent / "fixtures" / "sample_task"


def write_policy(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def base_policy(**overrides) -> dict:
    data = {
        "task_type": "t",
        "title": "t",
        "fields": [{"name": "a", "label": "에이", "question": "에이는?"}],
    }
    data.update(overrides)
    return data


def test_load_sample_policy():
    policy = load_policy(SAMPLE_DIR / "policy.yaml")
    assert [f.name for f in policy.fields] == ["idea", "customer", "problem", "tone", "length"]
    assert policy.field("length").kind is FieldKind.DEFAULT
    assert policy.question_caps[CoachingMode.QUICK] == 2
    assert policy.labels["customer"] == "목표 고객"
    assert policy.llm_validation is False


def test_default_caps_when_omitted(tmp_path):
    policy = load_policy(write_policy(tmp_path, base_policy()))
    assert policy.question_caps == {
        CoachingMode.QUICK: 3,
        CoachingMode.STANDARD: 5,
        CoachingMode.PRECISE: 10,
    }


def test_duplicate_field_names_rejected(tmp_path):
    fields = [{"name": "a", "label": "에이", "question": "?"}] * 2
    with pytest.raises(ValidationError, match="중복"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


def test_default_kind_requires_default_value(tmp_path):
    fields = [{"name": "a", "label": "에이", "kind": "default"}]
    with pytest.raises(ValidationError, match="default"):
        load_policy(write_policy(tmp_path, base_policy(fields=fields)))


def test_unknown_raw_input_field_rejected(tmp_path):
    with pytest.raises(ValidationError, match="raw_input_field"):
        load_policy(write_policy(tmp_path, base_policy(raw_input_field="nope")))


def test_partial_question_caps_rejected(tmp_path):
    with pytest.raises(ValidationError, match="question_caps"):
        load_policy(write_policy(tmp_path, base_policy(question_caps={"standard": 5})))


def sample_context() -> dict:
    policy = load_policy(SAMPLE_DIR / "policy.yaml")
    state = SessionState(task_type="sample_task", raw_input="집들이 선물용 향초")
    state.facts["idea"] = InfoItem(value="향초", source=InfoSource.USER_FREE_TEXT)
    return {
        "state": state,
        "policy": policy,
        "profile": state.profile,
        "field": policy.field("customer"),
        "level": 3,
        "previous": ["이전 질문"],
        "output_schema": "{}",
        "result_text": "결과 본문",
    }


@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_renders(stage):
    text = PromptRenderer(SAMPLE_DIR / "prompts").render(stage, **sample_context())
    assert "집들이 선물용 향초" in text
    assert "아이디어: 향초" in text


def test_task_template_overrides_common_and_keeps_base():
    text = PromptRenderer(SAMPLE_DIR / "prompts").render("generate", **sample_context())
    assert "샘플 지침 문구" in text
    assert "근거 없는 숫자를 사실처럼 쓰지 않는다" in text


def test_missing_task_template_falls_back_to_common(tmp_path):
    text = PromptRenderer(tmp_path / "prompts").render("generate", **sample_context())
    assert "샘플 지침 문구" not in text
    assert "출력 형식" in text
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_policy_prompting.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.harness'`

- [ ] **Step 4: 정책 로더 구현**

`backend/app/harness/policy.py`:
```python
"""과제별 policy.yaml을 읽고 검증한다. fields의 순서가 곧 고정 질문 우선순위다."""
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator

from app.core.state import CoachingMode


class FieldKind(StrEnum):
    MUST_CONFIRM = "must_confirm"  # 없으면 반드시 묻는다
    AI_SUGGEST = "ai_suggest"  # 후보를 제시하고 고르게 한다
    DEFAULT = "default"  # 기본값을 자동 적용하고 묻지 않는다


class LadderStep(BaseModel):
    question: str
    options: list[str] = Field(default_factory=list)


class FieldPolicy(BaseModel):
    name: str
    label: str
    kind: FieldKind = FieldKind.MUST_CONFIRM
    weight: float = Field(default=1.0, gt=0)
    question: str = ""
    options: list[str] = Field(default_factory=list)
    multi_select: bool = False
    easier_questions: list[LadderStep] = Field(default_factory=list)
    default: str | None = None

    @model_validator(mode="after")
    def _check_kind(self) -> "FieldPolicy":
        if self.kind is FieldKind.DEFAULT and self.default is None:
            raise ValueError(f"{self.name}: kind=default이면 default 값이 필요합니다")
        if self.kind is not FieldKind.DEFAULT and not self.question:
            raise ValueError(f"{self.name}: 질문 문구(question)가 필요합니다")
        return self


def _default_caps() -> dict[CoachingMode, int]:
    return {CoachingMode.QUICK: 3, CoachingMode.STANDARD: 5, CoachingMode.PRECISE: 10}


class TaskPolicy(BaseModel):
    task_type: str
    title: str
    description: str = ""
    input_placeholder: str = ""
    input_examples: list[str] = Field(default_factory=list)
    raw_input_field: str | None = None  # 첫 한 줄 입력을 사실로 둘 필드
    readiness_threshold: float = Field(default=0.7, ge=0, le=1)
    question_caps: dict[CoachingMode, int] = Field(default_factory=_default_caps)
    max_easier_level: int = Field(default=4, ge=1)  # 이 단계부터 AI 후보 제안
    llm_validation: bool = False  # 생성 후 LLM 검토 호출 (비용 때문에 기본 꺼짐)
    fields: list[FieldPolicy]
    rules: list[str] = Field(default_factory=list)  # 금지·주의 규칙

    @model_validator(mode="after")
    def _check_fields(self) -> "TaskPolicy":
        names = [f.name for f in self.fields]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"필드 이름이 중복됩니다: {duplicates}")
        if self.raw_input_field is not None and self.raw_input_field not in names:
            raise ValueError(f"raw_input_field '{self.raw_input_field}'가 fields에 없습니다")
        missing = sorted(set(CoachingMode) - set(self.question_caps))
        if missing:
            raise ValueError(f"question_caps에 모드가 빠졌습니다: {missing}")
        return self

    def field(self, name: str) -> FieldPolicy:
        for f in self.fields:
            if f.name == name:
                return f
        raise KeyError(name)

    @property
    def labels(self) -> dict[str, str]:
        return {f.name: f.label for f in self.fields}


def load_policy(path: Path) -> TaskPolicy:
    with path.open(encoding="utf-8") as fp:
        return TaskPolicy.model_validate(yaml.safe_load(fp))
```

- [ ] **Step 5: 프롬프트 렌더러와 공통 템플릿 구현**

`backend/app/harness/prompting.py`:
```python
"""프롬프트 템플릿 렌더링. 과제 폴더 prompts/가 공통 harness/prompts/보다 우선한다."""
from pathlib import Path
from typing import Any

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined

COMMON_PROMPTS_DIR = Path(__file__).parent / "prompts"
STAGES = ("diagnose", "easier_question", "propose_value", "generate", "validate")


class PromptRenderer:
    def __init__(self, task_prompts_dir: Path) -> None:
        self.env = Environment(
            loader=ChoiceLoader(
                [FileSystemLoader(task_prompts_dir), FileSystemLoader(COMMON_PROMPTS_DIR)]
            ),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            autoescape=False,
        )

    def render(self, stage: str, **context: Any) -> str:
        return self.env.get_template(f"{stage}.md").render(**context)
```

`backend/app/harness/prompts/_context.md`:
```markdown
## 과제
{{ policy.title }} — {{ policy.description }}

## 사용자가 처음 입력한 내용
{{ state.raw_input }}

## 확인된 사실
{% for name, item in state.facts.items() -%}
- {{ policy.labels.get(name, name) }}: {{ item.value }} (출처: {{ item.source }})
{% else -%}
- (없음)
{% endfor %}
## AI 가정 (사용자 확인 전)
{% for name, item in state.assumptions.items() -%}
- {{ policy.labels.get(name, name) }}: {{ item.value }}
{% else -%}
- (없음)
{% endfor %}
## 아직 모르는 항목
{% for name in state.unknowns -%}
- {{ policy.labels.get(name, name) }}
{% else -%}
- (없음)
{% endfor %}
```

`backend/app/harness/prompts/diagnose.md`:
```markdown
{% include "_context.md" %}
## 할 일
사용자의 처음 입력에서 아래 항목에 해당하는 정보를 찾아라. 입력에 분명히 있는 것만 뽑고 추측으로 채우지 마라.
{% for f in policy.fields -%}
- {{ f.name }}: {{ f.label }}
{% endfor %}
뜻이 모호한 표현은 ambiguous에 그대로 적어라.
```

`backend/app/harness/prompts/easier_question.md`:
```markdown
{% include "_context.md" %}
## 할 일
사용자가 "{{ field.label }}" 항목에 대해 아래 질문들에 "모르겠어요"라고 답했다.
{% for q in previous -%}
- {{ q }}
{% else -%}
- (없음)
{% endfor %}
이보다 한 단계 더 쉬운 질문 하나를 만들어라. 추상적인 질문 대신 구체적인 예시나 비교 선택으로 바꾸고, 고를 수 있는 선택지를 {{ profile.alternative_count }}~5개 함께 제시하라.
현재 쉬운 질문 단계: {{ level }}
```

`backend/app/harness/prompts/propose_value.md`:
```markdown
{% include "_context.md" %}
## 할 일
사용자가 "{{ field.label }}" 항목에 여러 번 "모르겠어요"라고 답했다. 지금까지의 맥락으로 가장 그럴듯한 후보 값을 {{ profile.alternative_count }}개 제안하라.
이미 제시했지만 고르지 않은 후보는 다시 내지 마라:
{% for c in previous -%}
- {{ c }}
{% else -%}
- (없음)
{% endfor %}
text에는 "이 중 가장 가까운 걸 고르거나 고쳐 주세요"처럼 고르기 쉬운 안내 문장을 써라.
현재 쉬운 질문 단계: {{ level }}
```

`backend/app/harness/prompts/_generate_base.md`:
```markdown
{% include "_context.md" %}
## 지켜야 할 규칙
{% for rule in policy.rules -%}
- {{ rule }}
{% endfor -%}
- 확인된 사실을 중심으로 작성한다. 사실이 아닌 내용을 보완했다면 assumptions에 반드시 적는다.
- 아직 모르는 항목은 지어내지 말고, 필요하면 실행 과제 카드로 "확인할 것"을 제안한다.

## 사용자 선호
- 상세도: {{ profile.preferred_detail }} / 피드백 강도: {{ profile.feedback_tone }} / 결과 형식: {{ profile.result_format }}
{% block task_guidance %}{% endblock %}
## 출력 형식
아래 JSON Schema를 따르는 JSON 하나만 출력하라.
{{ output_schema }}
```

`backend/app/harness/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
```

`backend/app/harness/prompts/validate.md`:
```markdown
{% include "_context.md" %}
## 지켜야 할 규칙
{% for rule in policy.rules -%}
- {{ rule }}
{% else -%}
- (없음)
{% endfor %}
## 검토할 결과
{{ result_text }}

## 할 일
결과가 입력과 모순되는지, 확인되지 않은 숫자를 사실처럼 썼는지, 과장·단정 표현이 있는지, 가정 표시가 빠졌는지 검토해 issues로 적어라.
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_policy_prompting.py -v`
Expected: 13 passed

- [ ] **Step 7: Commit**

```bash
git add backend/app/harness backend/tests/fixtures backend/tests/test_policy_prompting.py
git commit -m "feat: 과제 정책 로더와 프롬프트 렌더러 추가"
```

---

### Task 4: BaseHarness — 질문 진행과 '모르겠어요' 사다리

**Files:**
- Create: `backend/app/harness/errors.py`, `backend/app/harness/stage_models.py`, `backend/app/harness/base.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_harness_questions.py`, `backend/tests/test_harness_ladder.py`

**Interfaces:**
- Consumes: Task 1 상태 모델, Task 2 `LLMProvider`·`MockProvider`, Task 3 `load_policy`·`PromptRenderer`·`FieldKind`·`FieldPolicy`
- Produces:
  - `app.harness.errors`: `HarnessError`, `GenerationFailed`, `UnknownTaskError(LookupError)`
  - `app.harness.stage_models`: `ExtractedField`, `Diagnosis`, `GeneratedQuestion`(text, options), `ProposedValues`(text, candidates), `LLMReview`(issues)
  - `app.harness.base.BaseHarness(task_dir: Path, provider: LLMProvider)`
    - 클래스 속성 `content_model: ClassVar[type[BaseModel]]`
    - `policy`, `provider`, `prompts`, `task_type`
    - `start(raw_input: str, mode: CoachingMode = STANDARD, profile: HarnessProfile | None = None) -> SessionState`
    - `apply_answer(state, answer: Answer) -> None`, `revise_answer(state, answer: Answer) -> None`
    - `advance(state) -> None`, `select_question(state) -> Question | None`
    - `make_easier_question(state, field: FieldPolicy, level: int) -> Question`, `propose_value(state, field, level) -> Question`
    - `readiness(state) -> float`, `should_stop(state) -> bool`, `asked_count(state) -> int`, `question_cap(state) -> int`
  - `tests/conftest.py`: 픽스처 `provider`(MockProvider), `harness`(SampleHarness), `reply`(답변 도우미), 상수 `SAMPLE_TASK_DIR`, 클래스 `SampleContent`, `SampleHarness`

- [ ] **Step 1: 테스트 공용 픽스처 작성**

`backend/tests/conftest.py`:
```python
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from app.core.state import Answer, AnswerType, SessionState
from app.harness.base import BaseHarness
from app.providers.mock import MockProvider

SAMPLE_TASK_DIR = Path(__file__).parent / "fixtures" / "sample_task"


class SampleContent(BaseModel):
    summary: str = Field(description="요약")
    actions: list[str] = Field(description="실행 과제")


class SampleHarness(BaseHarness):
    content_model = SampleContent


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def harness(provider) -> SampleHarness:
    return SampleHarness(SAMPLE_TASK_DIR, provider)


@pytest.fixture
def reply():
    """지금 걸려 있는 질문에 답한다."""

    def _reply(
        harness: BaseHarness,
        state: SessionState,
        answer_type: AnswerType,
        value: str | None = None,
        option_ids: tuple[str, ...] = (),
    ) -> None:
        harness.apply_answer(
            state,
            Answer(
                question_id=state.pending_question.question_id,
                answer_type=answer_type,
                value=value,
                option_ids=list(option_ids),
            ),
        )

    return _reply
```

- [ ] **Step 2: 질문 진행 테스트 작성**

`backend/tests/test_harness_questions.py`:
```python
import pytest

from app.core.results import GenerationResult
from app.core.state import (
    Answer,
    AnswerType,
    Assumption,
    CoachingMode,
    InfoSource,
    SessionStatus,
)
from app.harness.errors import HarnessError


def test_start_sets_raw_input_fact_defaults_and_first_question(harness):
    state = harness.start("향초 만들기")

    assert state.facts["idea"].value == "향초 만들기"
    assert state.facts["idea"].source is InfoSource.USER_FREE_TEXT
    assert state.facts["length"].source is InfoSource.DEFAULT
    assert state.status is SessionStatus.CLARIFYING
    assert state.pending_question.field == "customer"
    assert [o.label for o in state.pending_question.options] == ["20대 직장인", "부모", "학생"]
    assert state.readiness == 0.4
    assert state.trace[0].stage == "diagnose"
    assert len(state.asked_questions) == 1


def test_option_answer_becomes_fact_and_moves_on(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o2",))

    assert state.facts["customer"].value == "부모"
    assert state.facts["customer"].source is InfoSource.USER_SELECTED_AI_OPTION
    assert state.pending_question.field == "problem"
    assert state.asked_questions[0].value == "부모"


def test_free_text_answer_is_stripped(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.FREE_TEXT, value="  집들이 가는 30대  ")
    assert state.facts["customer"].value == "집들이 가는 30대"
    assert state.facts["customer"].source is InfoSource.USER_FREE_TEXT


def test_invalid_answers_rejected(harness, reply):
    state = harness.start("향초")
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.FREE_TEXT, value="   ")
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION, option_ids=("o9",))
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION, option_ids=("o1", "o2"))
    with pytest.raises(HarnessError):
        reply(harness, state, AnswerType.OPTION)
    with pytest.raises(HarnessError):
        harness.apply_answer(state, Answer(question_id="q_다른질문", answer_type=AnswerType.SKIP))
    assert "customer" not in state.facts
    assert state.asked_questions[-1].answer_type is None


def test_stops_when_must_fields_filled_and_ready(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")

    assert state.readiness == 0.9
    assert state.pending_question is None
    assert state.status is SessionStatus.CONFIRMING


def test_stops_at_mode_question_cap(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    reply(harness, state, AnswerType.SKIP)
    reply(harness, state, AnswerType.SKIP)

    assert state.unknowns == ["customer", "problem"]
    assert harness.asked_count(state) == 2
    assert state.pending_question is None
    assert state.status is SessionStatus.CONFIRMING


def test_multi_select_joins_labels(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.SKIP)
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")
    assert state.pending_question.field == "tone"
    assert state.pending_question.multi_select

    reply(harness, state, AnswerType.OPTION, option_ids=("o1", "o3"))
    assert state.facts["tone"].value == "따뜻한, 유쾌한"


def test_assumption_offered_as_first_option(harness, reply):
    state = harness.start("향초")
    state.assumptions["customer"] = Assumption(
        value="30대 직장인", source=InfoSource.AI_ASSUMPTION, confidence=0.5
    )
    harness.advance(state)

    first = state.pending_question.options[0]
    assert (first.id, first.label, first.ai_suggested) == ("assumed", "30대 직장인", True)
    assert state.readiness == 0.55
    assert len(state.asked_questions) == 1

    reply(harness, state, AnswerType.OPTION, option_ids=("assumed",))
    assert state.facts["customer"].value == "30대 직장인"
    assert "customer" not in state.assumptions


def test_revise_answer_updates_fact(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    question_id = state.asked_questions[0].question.question_id

    harness.revise_answer(
        state, Answer(question_id=question_id, answer_type=AnswerType.FREE_TEXT, value="40대 부모")
    )

    assert state.facts["customer"].value == "40대 부모"
    assert state.asked_questions[0].value == "40대 부모"
    assert state.pending_question.field == "problem"


def test_revise_rejects_unknown_unanswered_and_non_value_answers(harness, reply):
    state = harness.start("향초")
    with pytest.raises(HarnessError):
        harness.revise_answer(state, Answer(question_id="q_없음", answer_type=AnswerType.FREE_TEXT, value="x"))
    with pytest.raises(HarnessError):
        harness.revise_answer(
            state,
            Answer(question_id=state.pending_question.question_id, answer_type=AnswerType.FREE_TEXT, value="x"),
        )
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    with pytest.raises(HarnessError):
        harness.revise_answer(
            state,
            Answer(question_id=state.asked_questions[0].question.question_id, answer_type=AnswerType.DONT_KNOW),
        )


def test_revise_after_result_marks_stale(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    reply(harness, state, AnswerType.FREE_TEXT, value="선물 고르기가 어렵다")
    state.result = GenerationResult(cards=[], full_text="이전 결과", content={})

    harness.revise_answer(
        state,
        Answer(
            question_id=state.asked_questions[0].question.question_id,
            answer_type=AnswerType.FREE_TEXT,
            value="40대 부모",
        ),
    )

    assert state.result_stale
    assert state.status is SessionStatus.REVISING
```

- [ ] **Step 3: 사다리 테스트 작성**

`backend/tests/test_harness_ladder.py`:
```python
from app.core.state import AnswerType, CoachingMode, InfoSource


def test_dont_know_walks_down_the_ladder_and_stays_on_field(harness, reply):
    state = harness.start("향초")

    reply(harness, state, AnswerType.DONT_KNOW)
    q1 = state.pending_question
    assert (q1.field, q1.level) == ("customer", 1)
    assert q1.text == "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?"

    reply(harness, state, AnswerType.DONT_KNOW)
    q2 = state.pending_question
    assert (q2.field, q2.level) == ("customer", 2)
    assert [o.label for o in q2.options] == ["나 자신", "다른 사람"]

    reply(harness, state, AnswerType.DONT_KNOW)
    q3 = state.pending_question
    assert (q3.field, q3.level, q3.is_ai_proposal) == ("customer", 3, False)
    assert q3.text.startswith("[mock]")
    assert state.trace[-1].stage == "easier_question"
    assert "이걸 가장 먼저 선물하고 싶은 사람은 누구인가요?" in state.trace[-1].input["prompt"]

    reply(harness, state, AnswerType.DONT_KNOW)
    q4 = state.pending_question
    assert (q4.field, q4.level, q4.is_ai_proposal) == ("customer", 4, True)
    assert all(o.ai_suggested for o in q4.options)
    assert state.trace[-1].stage == "propose_value"


def test_proposal_repeats_with_previous_candidates_excluded(harness, reply):
    state = harness.start("향초")
    for _ in range(5):
        reply(harness, state, AnswerType.DONT_KNOW)

    q5 = state.pending_question
    assert (q5.field, q5.level, q5.is_ai_proposal) == ("customer", 5, True)
    first_candidate = state.asked_questions[-2].question.options[0].label
    assert first_candidate in state.trace[-1].input["prompt"]


def test_choosing_a_proposal_resolves_field(harness, reply):
    state = harness.start("향초")
    for _ in range(4):
        reply(harness, state, AnswerType.DONT_KNOW)
    option_id = state.pending_question.options[0].id

    reply(harness, state, AnswerType.OPTION, option_ids=(option_id,))

    assert state.facts["customer"].source is InfoSource.USER_SELECTED_AI_OPTION
    assert state.dont_know_levels == {}
    assert state.pending_question.field == "problem"


def test_ladder_retries_do_not_count_toward_cap(harness, reply):
    state = harness.start("향초", mode=CoachingMode.QUICK)
    for _ in range(5):
        reply(harness, state, AnswerType.DONT_KNOW)
    reply(harness, state, AnswerType.FREE_TEXT, value="30대 직장인")

    assert harness.asked_count(state) == 1
    assert state.pending_question.field == "problem"


def test_skip_leaves_the_ladder(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.DONT_KNOW)
    reply(harness, state, AnswerType.SKIP)

    assert state.unknowns == ["customer"]
    assert state.dont_know_levels == {}
    assert state.pending_question.field == "problem"
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_harness_questions.py tests/test_harness_ladder.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.harness.base'`

- [ ] **Step 5: 오류·단계 응답 모델 구현**

`backend/app/harness/errors.py`:
```python
class HarnessError(Exception):
    """사용자 입력이 하네스 규칙에 맞지 않는다 (API에서 422)."""


class GenerationFailed(Exception):
    """결과 생성이 실패했다. 세션 입력은 보존된다 (API에서 502)."""


class UnknownTaskError(LookupError):
    """등록되지 않은 과제 유형이다 (API에서 404)."""
```

`backend/app/harness/stage_models.py`:
```python
"""LLM 단계별 응답 형태. Provider에 response_model로 넘긴다."""
from pydantic import BaseModel, Field

from app.core.results import ValidationIssue


class ExtractedField(BaseModel):
    field: str = Field(description="policy 필드 이름")
    value: str = Field(description="입력에서 찾은 값")


class Diagnosis(BaseModel):
    extracted: list[ExtractedField] = Field(
        default_factory=list, description="입력에서 분명히 확인되는 항목"
    )
    ambiguous: list[str] = Field(default_factory=list, description="뜻이 모호한 표현")


class GeneratedQuestion(BaseModel):
    text: str = Field(description="더 쉬운 질문 문구")
    options: list[str] = Field(default_factory=list, description="고를 수 있는 선택지")


class ProposedValues(BaseModel):
    text: str = Field(description="후보를 고르게 하는 안내 문장")
    candidates: list[str] = Field(description="AI가 제안하는 후보 값")


class LLMReview(BaseModel):
    issues: list[ValidationIssue] = Field(default_factory=list, description="발견한 문제")
```

- [ ] **Step 6: BaseHarness(질문 진행) 구현**

`backend/app/harness/base.py`:
```python
"""모든 과제가 공유하는 하네스 파이프라인.

단계 하나 = 메서드 하나다. 과제 하네스(tasks/<task>/harness.py)는 바꾸고 싶은
단계만 오버라이드한다. 모든 LLM 호출은 _call()을 거쳐 trace에 남는다.
"""
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from app.core.results import utcnow
from app.core.state import (
    Answer,
    AnswerType,
    AskedQuestion,
    Assumption,
    CoachingMode,
    HarnessProfile,
    InfoItem,
    InfoSource,
    Question,
    QuestionOption,
    SessionState,
    SessionStatus,
    TraceEntry,
)
from app.harness.errors import HarnessError
from app.harness.policy import FieldKind, FieldPolicy, load_policy
from app.harness.prompting import PromptRenderer
from app.harness.stage_models import Diagnosis, GeneratedQuestion, ProposedValues
from app.providers.base import LLMProvider, ProviderError

M = TypeVar("M", bound=BaseModel)


def _options(labels: list[str]) -> list[QuestionOption]:
    return [QuestionOption(id=f"o{i}", label=label) for i, label in enumerate(labels, start=1)]


class BaseHarness:
    content_model: ClassVar[type[BaseModel]]

    def __init__(self, task_dir: Path, provider: LLMProvider) -> None:
        self.task_dir = task_dir
        self.policy = load_policy(task_dir / "policy.yaml")
        self.provider = provider
        self.prompts = PromptRenderer(task_dir / "prompts")

    @property
    def task_type(self) -> str:
        return self.policy.task_type

    # ── 세션 시작 ──────────────────────────────────────────────

    def start(
        self,
        raw_input: str,
        mode: CoachingMode = CoachingMode.STANDARD,
        profile: HarnessProfile | None = None,
    ) -> SessionState:
        state = SessionState(
            task_type=self.task_type,
            mode=mode,
            raw_input=raw_input,
            profile=profile or HarnessProfile(),
        )
        self.apply_defaults(state)
        self.diagnose(state)
        self.advance(state)
        return state

    def apply_defaults(self, state: SessionState) -> None:
        """[코드] kind=default 필드는 묻지 않고 기본값을 넣는다."""
        for f in self.policy.fields:
            if f.kind is FieldKind.DEFAULT and f.default is not None:
                state.facts[f.name] = InfoItem(value=f.default, source=InfoSource.DEFAULT)

    def diagnose(self, state: SessionState) -> None:
        """[LLM] 처음 입력에서 항목을 뽑는다. 뽑은 값은 확인 전이므로 가정으로만 둔다."""
        target = self.policy.raw_input_field
        if target and state.raw_input.strip():
            state.facts[target] = InfoItem(
                value=state.raw_input.strip(), source=InfoSource.USER_FREE_TEXT
            )
        diagnosis = self._call(state, "diagnose", Diagnosis)
        known = set(self.policy.labels)
        for item in diagnosis.extracted:
            if item.field in known and item.field not in state.facts:
                state.assumptions[item.field] = Assumption(
                    value=item.value,
                    source=InfoSource.AI_ASSUMPTION,
                    confidence=0.5,
                    reason="처음 입력에서 추출",
                )

    # ── 질문 ──────────────────────────────────────────────────

    def advance(self, state: SessionState) -> None:
        """준비도를 갱신하고 다음 질문을 정한다. 답하지 않은 이전 질문은 버린다."""
        self._drop_unanswered(state)
        state.readiness = self.readiness(state)
        question = self.select_question(state)
        state.pending_question = question
        if question is not None:
            state.asked_questions.append(AskedQuestion(question=question))
            state.status = SessionStatus.CLARIFYING
        else:
            state.status = SessionStatus.REVISING if state.result_stale else SessionStatus.CONFIRMING

    def select_question(self, state: SessionState) -> Question | None:
        """[코드] '모르겠어요' 중인 필드가 먼저, 그다음 policy 순서대로 미충족 필드."""
        if state.dont_know_levels:
            name, level = next(iter(state.dont_know_levels.items()))
            return self.make_easier_question(state, self.policy.field(name), level)
        if self.should_stop(state):
            return None
        remaining = self.remaining_fields(state)
        return self.base_question(state, remaining[0]) if remaining else None

    def remaining_fields(self, state: SessionState) -> list[FieldPolicy]:
        return [
            f
            for f in self.policy.fields
            if f.kind is not FieldKind.DEFAULT
            and f.name not in state.facts
            and f.name not in state.unknowns
        ]

    def base_question(self, state: SessionState, field: FieldPolicy) -> Question:
        options = _options(field.options)
        assumed = state.assumptions.get(field.name)
        if assumed is not None:
            options.insert(0, QuestionOption(id="assumed", label=assumed.value, ai_suggested=True))
        return Question(
            field=field.name, text=field.question, options=options, multi_select=field.multi_select
        )

    def make_easier_question(self, state: SessionState, field: FieldPolicy, level: int) -> Question:
        """'모르겠어요' 사다리: policy 사다리 → LLM 쉬운 질문 → AI 후보 제안 순으로 내려간다."""
        if level >= self.policy.max_easier_level:
            return self.propose_value(state, field, level)
        if level <= len(field.easier_questions):
            step = field.easier_questions[level - 1]
            return Question(
                field=field.name,
                text=step.question,
                options=_options(step.options),
                multi_select=field.multi_select,
                level=level,
            )
        generated = self._call(
            state,
            "easier_question",
            GeneratedQuestion,
            field=field,
            level=level,
            previous=self._asked_texts(state, field.name),
        )
        return Question(
            field=field.name,
            text=generated.text,
            options=_options(generated.options),
            multi_select=field.multi_select,
            level=level,
        )

    def propose_value(self, state: SessionState, field: FieldPolicy, level: int) -> Question:
        """[LLM] 사다리 바닥. 맥락으로 후보를 추정해 고르거나 고치게 한다."""
        proposed = self._call(
            state,
            "propose_value",
            ProposedValues,
            field=field,
            level=level,
            previous=self._proposed_labels(state, field.name),
        )
        options = [
            QuestionOption(id=f"p{level}_{i}", label=label, ai_suggested=True)
            for i, label in enumerate(proposed.candidates, start=1)
        ]
        return Question(
            field=field.name, text=proposed.text, options=options, level=level, is_ai_proposal=True
        )

    # ── 답변 ──────────────────────────────────────────────────

    def apply_answer(self, state: SessionState, answer: Answer) -> None:
        question = state.pending_question
        if question is None or question.question_id != answer.question_id:
            raise HarnessError("지금 답할 수 있는 질문이 아닙니다.")
        name = question.field
        value: str | None = None

        match answer.answer_type:
            case AnswerType.OPTION:
                value = self._option_value(question, answer.option_ids)
                self._set_fact(state, name, value, InfoSource.USER_SELECTED_AI_OPTION)
            case AnswerType.FREE_TEXT:
                value = self._free_text(answer.value)
                self._set_fact(state, name, value, InfoSource.USER_FREE_TEXT)
            case AnswerType.DONT_KNOW:
                state.dont_know_levels[name] = question.level + 1
            case AnswerType.SKIP:
                state.dont_know_levels.pop(name, None)
                if name not in state.unknowns:
                    state.unknowns.append(name)

        record = state.asked_questions[-1]
        record.answer_type = answer.answer_type
        record.value = value
        record.answered_at = utcnow()
        self.advance(state)

    def revise_answer(self, state: SessionState, answer: Answer) -> None:
        """이전 답변 수정(IV-08). 결과가 이미 있으면 재생성이 필요하다고 표시한다."""
        record = state.find_asked(answer.question_id)
        if record is None or record.answer_type is None:
            raise HarnessError("수정할 수 있는 답변이 아닙니다.")
        name = record.question.field

        match answer.answer_type:
            case AnswerType.OPTION:
                value = self._option_value(record.question, answer.option_ids)
                self._set_fact(state, name, value, InfoSource.USER_SELECTED_AI_OPTION)
            case AnswerType.FREE_TEXT:
                value = self._free_text(answer.value)
                self._set_fact(state, name, value, InfoSource.USER_FREE_TEXT)
            case _:
                raise HarnessError("수정은 선택지나 직접 입력으로만 할 수 있습니다.")

        record.answer_type = answer.answer_type
        record.value = value
        record.answered_at = utcnow()
        self.advance(state)

    # ── 준비도·종료 ───────────────────────────────────────────

    def readiness(self, state: SessionState) -> float:
        """[코드] 채워진 필드 가중치 비율. 사실 1.0, AI 가정 0.5, 미확인 0."""
        total = sum(f.weight for f in self.policy.fields)
        score = sum(
            f.weight
            * (1.0 if f.name in state.facts else 0.5 if f.name in state.assumptions else 0.0)
            for f in self.policy.fields
        )
        return round(score / total, 3) if total else 0.0

    def question_cap(self, state: SessionState) -> int:
        return self.policy.question_caps[state.mode]

    def asked_count(self, state: SessionState) -> int:
        """질문 상한에 세는 수: 답한 기본 질문. '모르겠어요' 재질문(level ≥ 1)과 지금 걸려 있는 질문은 세지 않는다."""
        return sum(
            1 for a in state.asked_questions if a.question.level == 0 and a.answer_type is not None
        )

    def should_stop(self, state: SessionState) -> bool:
        if self.asked_count(state) >= self.question_cap(state):
            return True
        musts = [f.name for f in self.policy.fields if f.kind is FieldKind.MUST_CONFIRM]
        return (
            all(name in state.facts for name in musts)
            and state.readiness >= self.policy.readiness_threshold
        )

    # ── 내부 도우미 ───────────────────────────────────────────

    def _call(self, state: SessionState, stage: str, response_model: type[M], **context: Any) -> M:
        """프롬프트를 렌더링해 Provider를 부르고, 성공이든 실패든 trace에 남긴다."""
        prompt = self.prompts.render(
            stage, state=state, policy=self.policy, profile=state.profile, **context
        )
        try:
            response = self.provider.complete(
                task_type=self.task_type, stage=stage, prompt=prompt, response_model=response_model
            )
        except ProviderError as exc:
            state.trace.append(
                TraceEntry(
                    stage=stage,
                    input={"prompt": prompt},
                    output={"error": str(exc)},
                    provider=self.provider.name,
                )
            )
            raise
        state.trace.append(
            TraceEntry(
                stage=stage,
                input={"prompt": prompt},
                output=response.parsed.model_dump(mode="json") if response.parsed else {"text": response.text},
                provider=response.model,
                usage=response.usage.model_dump(),
            )
        )
        return response.parsed  # type: ignore[return-value]

    def _drop_unanswered(self, state: SessionState) -> None:
        if state.asked_questions and state.asked_questions[-1].answer_type is None:
            state.asked_questions.pop()
        state.pending_question = None

    def _set_fact(self, state: SessionState, name: str, value: str, source: InfoSource) -> None:
        state.facts[name] = InfoItem(value=value, source=source)
        state.assumptions.pop(name, None)
        state.dont_know_levels.pop(name, None)
        if name in state.unknowns:
            state.unknowns.remove(name)
        if state.result is not None:
            state.result_stale = True

    @staticmethod
    def _option_value(question: Question, option_ids: list[str]) -> str:
        if not option_ids:
            raise HarnessError("선택한 선택지가 없습니다.")
        if len(option_ids) > 1 and not question.multi_select:
            raise HarnessError("이 질문은 하나만 고를 수 있습니다.")
        labels = {o.id: o.label for o in question.options}
        unknown = [i for i in option_ids if i not in labels]
        if unknown:
            raise HarnessError(f"없는 선택지입니다: {unknown}")
        return ", ".join(labels[i] for i in option_ids)

    @staticmethod
    def _free_text(value: str | None) -> str:
        text = (value or "").strip()
        if not text:
            raise HarnessError("직접 입력한 내용이 비어 있습니다.")
        return text

    @staticmethod
    def _asked_texts(state: SessionState, name: str) -> list[str]:
        return [a.question.text for a in state.asked_questions if a.question.field == name]

    @staticmethod
    def _proposed_labels(state: SessionState, name: str) -> list[str]:
        return [
            o.label
            for a in state.asked_questions
            if a.question.field == name and a.question.is_ai_proposal
            for o in a.question.options
        ]
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_harness_questions.py tests/test_harness_ladder.py -v`
Expected: 16 passed

- [ ] **Step 8: 전체 테스트 확인**

Run: `uv run --directory backend pytest`
Expected: 38 passed

- [ ] **Step 9: Commit**

```bash
git add backend/app/harness backend/tests
git commit -m "feat: 하네스 공통 파이프라인 질문 진행과 모르겠어요 사다리 구현"
```

---

### Task 5: BaseHarness — 결과 생성·검증과 시나리오 실행기

**Files:**
- Create: `backend/app/harness/validation.py`, `backend/app/harness/evals.py`
- Modify: `backend/app/harness/base.py` (import 추가, `__init__`에 `result_model`, 클래스 속성 `validators`, 생성·검증 메서드 추가)
- Create: `backend/tests/fixtures/sample_task/evals/basic.yaml`
- Test: `backend/tests/test_harness_generate.py`

**Interfaces:**
- Consumes: Task 4 `BaseHarness`와 그 내부 `_call`, `_drop_unanswered`
- Produces:
  - `app.harness.validation`: `Validator = Callable[[SessionState, GenerationResult, TaskPolicy], list[ValidationIssue]]`, `check_cards_present`, `check_assumptions_marked`, `COMMON_VALIDATORS`
  - `BaseHarness.validators: ClassVar[list[Validator]]`(기본 `[]`), `BaseHarness.result_model`(= `TaskResult[content_model]`), `generate(state) -> None`(실패 시 `GenerationFailed`), `validate(state, result: GenerationResult) -> ValidationReport`
  - `app.harness.evals`: `ScenarioAnswer`(answer_type, value, option_indexes), `Scenario`(name, raw_input, mode, answers: dict[str, list[ScenarioAnswer]], expect_status), `load_scenarios(task_dir: Path) -> list[Scenario]`, `run_scenario(harness, scenario, max_turns=50) -> SessionState`

- [ ] **Step 1: 시나리오 픽스처 작성**

`backend/tests/fixtures/sample_task/evals/basic.yaml`:
```yaml
name: 모르겠어요 한 번 후 직접 입력
raw_input: 집들이 선물용 향초
answers:
  customer:
    - answer_type: dont_know
    - value: 집들이 가는 30대
  problem:
    - value: 선물 고르기가 어렵다
```

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/test_harness_generate.py`:
```python
import pytest

from app.core.results import ValidationIssue
from app.core.state import Answer, AnswerType, Assumption, InfoSource, SessionStatus
from app.harness.errors import GenerationFailed
from app.harness.evals import load_scenarios, run_scenario
from app.providers.mock import MockProvider
from tests.conftest import SAMPLE_TASK_DIR, SampleHarness


def test_generate_completes_with_validated_result(harness):
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert state.result.content["summary"] == "[mock] 요약"
    assert state.result.cards
    assert state.validation.passed
    assert [t.stage for t in state.trace[-2:]] == ["generate", "validate"]


def test_generate_drops_pending_question(harness):
    state = harness.start("향초")
    harness.generate(state)
    assert state.pending_question is None
    assert all(a.answer_type is not None for a in state.asked_questions)


def test_generate_failure_preserves_input_and_can_retry():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"generate"}))
    state = harness.start("향초")

    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED
    assert state.error
    assert state.facts["idea"].value == "향초"
    assert state.trace[-1].output["error"]

    harness.provider = MockProvider()
    harness.generate(state)
    assert state.status is SessionStatus.COMPLETED
    assert state.error is None


def test_schema_error_retried_once():
    provider = MockProvider(output_errors={"generate": 1})
    harness = SampleHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert [s for _, s in provider.calls].count("generate") == 2


def test_schema_error_twice_fails():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(output_errors={"generate": 2}))
    state = harness.start("향초")
    with pytest.raises(GenerationFailed):
        harness.generate(state)
    assert state.status is SessionStatus.FAILED


def test_regenerate_clears_stale(harness, reply):
    state = harness.start("향초")
    reply(harness, state, AnswerType.OPTION, option_ids=("o1",))
    harness.generate(state)
    harness.revise_answer(
        state,
        Answer(question_id=state.asked_questions[0].question.question_id, answer_type=AnswerType.FREE_TEXT, value="부모"),
    )
    assert state.result_stale

    harness.generate(state)
    assert not state.result_stale


def test_task_validators_run(provider):
    def always_error(state, result, policy):
        return [ValidationIssue(rule="always", message="항상 실패", severity="error")]

    class StrictHarness(SampleHarness):
        validators = [always_error]

    harness = StrictHarness(SAMPLE_TASK_DIR, provider)
    state = harness.start("향초")
    harness.generate(state)
    assert not state.validation.passed
    assert state.status is SessionStatus.COMPLETED


def test_unmarked_assumption_is_flagged(harness):
    state = harness.start("향초")
    state.assumptions["customer"] = Assumption(value="30대", source=InfoSource.AI_ASSUMPTION)
    harness.generate(state)
    assert "assumptions_marked" in [i.rule for i in state.validation.issues]


def test_llm_validation_only_when_enabled(harness, provider):
    state = harness.start("향초")
    harness.generate(state)
    assert ("sample_task", "validate") not in provider.calls

    harness.policy.llm_validation = True
    harness.generate(state)
    assert ("sample_task", "validate") in provider.calls


def test_llm_validation_failure_becomes_warning():
    harness = SampleHarness(SAMPLE_TASK_DIR, MockProvider(fail_stages={"validate"}))
    harness.policy.llm_validation = True
    state = harness.start("향초")
    harness.generate(state)

    assert state.status is SessionStatus.COMPLETED
    assert "llm_review_unavailable" in [i.rule for i in state.validation.issues]


def test_sample_scenario_runs(harness):
    scenarios = load_scenarios(SAMPLE_TASK_DIR)
    assert [s.name for s in scenarios] == ["모르겠어요 한 번 후 직접 입력"]

    state = run_scenario(harness, scenarios[0])
    assert state.status is scenarios[0].expect_status
    assert state.facts["customer"].value == "집들이 가는 30대"
    assert state.facts["problem"].value == "선물 고르기가 어렵다"
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_harness_generate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.harness.evals'`

- [ ] **Step 4: 공통 검증 규칙 구현**

`backend/app/harness/validation.py`:
```python
"""모든 과제에 공통으로 적용하는 출력 검증 규칙. 과제 전용 규칙은 tasks/<task>/validators.py."""
from collections.abc import Callable

from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy

Validator = Callable[[SessionState, GenerationResult, TaskPolicy], list[ValidationIssue]]


def check_cards_present(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    if result.cards:
        return []
    return [ValidationIssue(rule="cards_present", message="결과 카드가 하나도 없습니다.", severity="error")]


def check_assumptions_marked(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    """세션에 AI 가정이 남아 있는데 결과에 가정 표시가 없으면 경고한다(설계서 12장)."""
    marked = {a.field for a in result.assumptions}
    missing = [name for name in state.assumptions if name not in marked]
    if not missing:
        return []
    labels = ", ".join(policy.labels.get(name, name) for name in missing)
    return [ValidationIssue(rule="assumptions_marked", message=f"AI 가정이 결과에 표시되지 않았습니다: {labels}")]


COMMON_VALIDATORS: list[Validator] = [check_cards_present, check_assumptions_marked]
```

- [ ] **Step 5: BaseHarness에 생성·검증 추가**

`backend/app/harness/base.py`의 import 블록을 다음으로 바꾼다:
```python
import json
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel

from app.core.results import (
    GenerationResult,
    TaskResult,
    ValidationIssue,
    ValidationReport,
    utcnow,
)
from app.core.state import (
    Answer,
    AnswerType,
    AskedQuestion,
    Assumption,
    CoachingMode,
    HarnessProfile,
    InfoItem,
    InfoSource,
    Question,
    QuestionOption,
    SessionState,
    SessionStatus,
    TraceEntry,
)
from app.harness.errors import GenerationFailed, HarnessError
from app.harness.policy import FieldKind, FieldPolicy, load_policy
from app.harness.prompting import PromptRenderer
from app.harness.stage_models import Diagnosis, GeneratedQuestion, LLMReview, ProposedValues
from app.harness.validation import COMMON_VALIDATORS, Validator
from app.providers.base import LLMProvider, ProviderError, ProviderOutputError
```

클래스 머리와 `__init__`를 다음으로 바꾼다:
```python
class BaseHarness:
    content_model: ClassVar[type[BaseModel]]
    validators: ClassVar[list[Validator]] = []

    def __init__(self, task_dir: Path, provider: LLMProvider) -> None:
        self.task_dir = task_dir
        self.policy = load_policy(task_dir / "policy.yaml")
        self.provider = provider
        self.prompts = PromptRenderer(task_dir / "prompts")
        self.result_model = TaskResult[self.content_model]
```

`should_stop` 메서드 바로 아래(`# ── 내부 도우미` 위)에 추가한다:
```python
    # ── 생성·검증 ─────────────────────────────────────────────

    def generate(self, state: SessionState) -> None:
        """[LLM] 현재 정보로 결과를 만든다. 언제든 부를 수 있다(설계서 원칙 8)."""
        self._drop_unanswered(state)
        state.status = SessionStatus.GENERATING
        schema = json.dumps(self.result_model.model_json_schema(), ensure_ascii=False, indent=2)
        try:
            try:
                parsed = self._call(state, "generate", self.result_model, output_schema=schema)
            except ProviderOutputError:
                parsed = self._call(state, "generate", self.result_model, output_schema=schema)
        except ProviderError as exc:
            state.status = SessionStatus.FAILED
            state.error = str(exc)
            raise GenerationFailed(str(exc)) from exc

        result = GenerationResult(
            cards=parsed.cards,
            assumptions=parsed.assumptions,
            full_text=parsed.full_text,
            content=parsed.content.model_dump(mode="json"),
        )
        state.result = result
        state.result_stale = False
        state.error = None
        state.validation = self.validate(state, result)
        state.status = SessionStatus.COMPLETED

    def validate(self, state: SessionState, result: GenerationResult) -> ValidationReport:
        """[코드 + LLM] 공통·과제 규칙을 돌린다. LLM 검토는 policy.llm_validation일 때만(비용)."""
        issues: list[ValidationIssue] = []
        for check in [*COMMON_VALIDATORS, *self.validators]:
            issues.extend(check(state, result, self.policy))
        if self.policy.llm_validation:
            try:
                review = self._call(state, "validate", LLMReview, result_text=result.full_text)
                issues.extend(review.issues)
            except ProviderError:
                issues.append(
                    ValidationIssue(rule="llm_review_unavailable", message="AI 검토를 하지 못했습니다.")
                )
        state.trace.append(
            TraceEntry(stage="validate", output={"issues": [i.model_dump() for i in issues]})
        )
        return ValidationReport(issues=issues)
```

- [ ] **Step 6: 시나리오 실행기 구현**

`backend/app/harness/evals.py`:
```python
"""과제 폴더 evals/*.yaml 시나리오를 하네스에 돌린다.

하네스를 고친 뒤 회귀 확인에 쓰고, 나중에 실제 모델이 붙으면 같은 시나리오로 품질을 비교한다.
"""
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from app.core.state import Answer, AnswerType, CoachingMode, SessionState, SessionStatus
from app.harness.base import BaseHarness


class ScenarioAnswer(BaseModel):
    answer_type: AnswerType = AnswerType.FREE_TEXT
    value: str | None = None
    option_indexes: list[int] = Field(default_factory=list)  # 0부터 센 선택지 위치


class Scenario(BaseModel):
    name: str
    raw_input: str
    mode: CoachingMode = CoachingMode.STANDARD
    answers: dict[str, list[ScenarioAnswer]] = Field(default_factory=dict)  # 필드별로 차례대로 쓸 답변
    expect_status: SessionStatus = SessionStatus.COMPLETED


def load_scenarios(task_dir: Path) -> list[Scenario]:
    scenarios = []
    for path in sorted((task_dir / "evals").glob("*.yaml")):
        with path.open(encoding="utf-8") as fp:
            scenarios.append(Scenario.model_validate(yaml.safe_load(fp)))
    return scenarios


def run_scenario(harness: BaseHarness, scenario: Scenario, max_turns: int = 50) -> SessionState:
    """시나리오에 없는 질문은 건너뛰고, 질문이 끝나면 결과를 생성한다."""
    state = harness.start(scenario.raw_input, scenario.mode)
    queues = {name: list(answers) for name, answers in scenario.answers.items()}
    for _ in range(max_turns):
        question = state.pending_question
        if question is None:
            break
        queue = queues.get(question.field)
        planned = queue.pop(0) if queue else ScenarioAnswer(answer_type=AnswerType.SKIP)
        harness.apply_answer(
            state,
            Answer(
                question_id=question.question_id,
                answer_type=planned.answer_type,
                value=planned.value,
                option_ids=[question.options[i].id for i in planned.option_indexes],
            ),
        )
    else:
        raise RuntimeError(f"시나리오 '{scenario.name}'가 {max_turns}턴 안에 끝나지 않았습니다.")
    harness.generate(state)
    return state
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_harness_generate.py -v`
Expected: 11 passed

- [ ] **Step 8: 전체 테스트 확인**

Run: `uv run --directory backend pytest`
Expected: 49 passed

- [ ] **Step 9: Commit**

```bash
git add backend/app/harness backend/tests
git commit -m "feat: 결과 생성·검증과 시나리오 실행기 추가"
```

---

### Task 6: 과제 4개 폴더와 등록부

**Files:**
- Create: `backend/app/harness/tasks/__init__.py`(빈 파일), `backend/app/harness/registry.py`
- Create (과제마다): `backend/app/harness/tasks/<task>/__init__.py`(빈 파일), `harness.py`, `output_schema.py`, `validators.py`, `policy.yaml`, `prompts/generate.md`, `evals/basic.yaml` — `<task>` = `business_plan`, `product_planning`, `branding`, `marketing_content`
- Test: `backend/tests/test_tasks.py`

**Interfaces:**
- Consumes: `BaseHarness`, `Validator`, `ValidationIssue`, `load_scenarios`, `run_scenario`, `PromptRenderer`·`STAGES`, `UnknownTaskError`
- Produces:
  - `app.harness.registry`: `TASKS_DIR`, `TASK_TYPES: tuple[str, ...]`, `build_harness(task_type, provider) -> BaseHarness`, `HarnessRegistry(provider)` + `get(task_type) -> BaseHarness`(없으면 `UnknownTaskError`), `all() -> list[BaseHarness]`
  - 각 과제 `harness.py`의 `Harness(BaseHarness)` 클래스, `validators.py`의 `VALIDATORS: list[Validator]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_tasks.py`:
```python
import pytest

from app.core.results import GenerationResult, ResultCard
from app.core.state import SessionState
from app.harness.errors import UnknownTaskError
from app.harness.evals import load_scenarios, run_scenario
from app.harness.policy import FieldKind
from app.harness.prompting import STAGES
from app.harness.registry import TASK_TYPES, TASKS_DIR, HarnessRegistry
from app.harness.tasks.business_plan.validators import check_unsupported_market_claims
from app.harness.tasks.marketing_content.validators import check_cta_present
from app.providers.mock import MockProvider


@pytest.fixture(scope="module")
def registry():
    return HarnessRegistry(MockProvider())


def test_registry_has_all_tasks(registry):
    assert [h.task_type for h in registry.all()] == list(TASK_TYPES)
    with pytest.raises(UnknownTaskError):
        registry.get("nope")


@pytest.mark.parametrize("task_type", TASK_TYPES)
def test_policy_is_complete(registry, task_type):
    policy = registry.get(task_type).policy
    assert policy.task_type == task_type
    assert policy.raw_input_field is not None
    assert policy.rules
    for field in policy.fields:
        if field.kind is FieldKind.MUST_CONFIRM:
            assert field.easier_questions, f"{field.name}: 반드시 확인 필드에는 쉬운 질문이 하나 이상 필요"


@pytest.mark.parametrize("task_type", TASK_TYPES)
@pytest.mark.parametrize("stage", STAGES)
def test_every_stage_template_renders(registry, task_type, stage):
    harness = registry.get(task_type)
    state = harness.start("테스트 입력")
    text = harness.prompts.render(
        stage,
        state=state,
        policy=harness.policy,
        profile=state.profile,
        field=harness.policy.fields[0],
        level=3,
        previous=[],
        output_schema="{}",
        result_text="결과",
    )
    assert "테스트 입력" in text


@pytest.mark.parametrize("task_type", TASK_TYPES)
def test_eval_scenarios_complete(registry, task_type):
    harness = registry.get(task_type)
    scenarios = load_scenarios(TASKS_DIR / task_type)
    assert scenarios
    for scenario in scenarios:
        state = run_scenario(harness, scenario)
        assert state.status is scenario.expect_status, scenario.name
        harness.content_model.model_validate(state.result.content)


def make_result(full_text: str = "본문", content: dict | None = None) -> GenerationResult:
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    return GenerationResult(cards=[card], full_text=full_text, content=content or {})


def test_business_plan_flags_market_claims(registry):
    policy = registry.get("business_plan").policy
    state = SessionState(task_type="business_plan")
    assert check_unsupported_market_claims(state, make_result("시장 규모는 1조 원"), policy)
    assert not check_unsupported_market_claims(state, make_result("고객 인터뷰부터"), policy)


def test_marketing_requires_cta(registry):
    policy = registry.get("marketing_content").policy
    state = SessionState(task_type="marketing_content")
    issues = check_cta_present(state, make_result(content={"cta": "  "}), policy)
    assert issues and issues[0].severity == "error"
    assert not check_cta_present(state, make_result(content={"cta": "프로필 링크에서 구매"}), policy)
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_tasks.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.harness.registry'`

- [ ] **Step 3: 등록부 구현**

`backend/app/harness/registry.py`:
```python
"""task_type → 과제 하네스. 새 과제는 tasks/ 아래 폴더를 만들고 TASK_TYPES에 추가한다."""
import importlib
from pathlib import Path

from app.harness.base import BaseHarness
from app.harness.errors import UnknownTaskError
from app.providers.base import LLMProvider

TASKS_DIR = Path(__file__).parent / "tasks"
TASK_TYPES = ("business_plan", "product_planning", "branding", "marketing_content")


def build_harness(task_type: str, provider: LLMProvider) -> BaseHarness:
    module = importlib.import_module(f"app.harness.tasks.{task_type}.harness")
    return module.Harness(TASKS_DIR / task_type, provider)


class HarnessRegistry:
    def __init__(self, provider: LLMProvider) -> None:
        self._harnesses = {t: build_harness(t, provider) for t in TASK_TYPES}

    def get(self, task_type: str) -> BaseHarness:
        try:
            return self._harnesses[task_type]
        except KeyError:
            raise UnknownTaskError(task_type) from None

    def all(self) -> list[BaseHarness]:
        return list(self._harnesses.values())
```

- [ ] **Step 4: 사업계획(business_plan) 과제 작성**

`backend/app/harness/tasks/business_plan/harness.py`:
```python
"""사업계획 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import BusinessPlanContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = BusinessPlanContent
    validators = VALIDATORS
```

`backend/app/harness/tasks/business_plan/output_schema.py`:
```python
"""사업계획 결과물. 이 모델이 하네스 설계의 기준점이다(필드 → 질문 → 검증이 여기서 파생)."""
from pydantic import BaseModel, Field


class BusinessPlanContent(BaseModel):
    customer_problem: str = Field(description="고객이 겪는 핵심 문제")
    target_customer: str = Field(description="가장 먼저 공략할 목표 고객")
    solution: str = Field(description="문제를 해결하는 방식")
    revenue_model: str = Field(description="수익을 내는 구조")
    risks: list[str] = Field(description="주요 위험과 불확실성")
    validation_plan: list[str] = Field(description="가설을 검증할 다음 행동")
```

`backend/app/harness/tasks/business_plan/validators.py`:
```python
"""사업계획 전용 검증 규칙(설계서 7.1 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator

UNSUPPORTED_CLAIMS = ("시장 규모", "매출 전망", "예상 매출")


def check_unsupported_market_claims(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    hits = [word for word in UNSUPPORTED_CLAIMS if word in result.full_text]
    if not hits:
        return []
    return [
        ValidationIssue(
            rule="unsupported_market_claims",
            message=f"근거 확인이 필요한 표현이 있습니다: {', '.join(hits)}. 출처가 없다면 가정으로 표시하세요.",
        )
    ]


VALIDATORS: list[Validator] = [check_unsupported_market_claims]
```

`backend/app/harness/tasks/business_plan/policy.yaml`:
```yaml
task_type: business_plan
title: 사업계획
description: 사업 가설과 실행 구조를 정리합니다.
input_placeholder: 예) 직접 만든 향초를 온라인으로 팔고 싶어요
input_examples:
  - 직접 만든 향초를 온라인으로 팔고 싶어요
  - 동네 반려견 산책 대행을 시작하려고 해요
raw_input_field: business_idea
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
max_easier_level: 4
fields:
  - name: business_idea
    label: 사업 아이디어
    kind: must_confirm
    weight: 3
    question: 어떤 사업을 하고 싶으신가요?
    easier_questions:
      - question: 팔고 싶은 물건이나 서비스를 하나만 말해 주세요.
  - name: customer_problem
    label: 고객 문제
    kind: must_confirm
    weight: 3
    question: 고객이 지금 겪고 있는 불편이나 문제는 무엇인가요?
    easier_questions:
      - question: 이 사업이 없으면 고객은 어떤 점이 아쉬울까요?
      - question: 아래 중 가장 가까운 불편을 골라 주세요.
        options: [시간이 오래 걸린다, 비용이 비싸다, 마음에 드는 선택지가 없다, 방법을 잘 모른다]
  - name: target_customer
    label: 목표 고객
    kind: must_confirm
    weight: 3
    question: 가장 먼저 팔고 싶은 고객은 누구인가요?
    options: [20~30대 직장인, 자녀를 둔 부모, 대학생, 소상공인]
    easier_questions:
      - question: 이 사업을 가장 반가워할 주변 사람 한 명을 떠올려 보세요. 어떤 사람인가요?
      - question: 둘 중 더 가까운 쪽을 골라 주세요.
        options: [개인 고객, 가게·회사 같은 사업자]
  - name: current_alternatives
    label: 현재 대안
    kind: ai_suggest
    weight: 1
    question: 고객은 지금 이 문제를 어떻게 해결하고 있나요?
    options: [비슷한 제품을 사서 쓴다, 직접 해결한다, 그냥 참는다]
    easier_questions:
      - question: 이 사업이 없다면 고객은 대신 무엇을 살까요?
  - name: solution
    label: 해결 방식
    kind: must_confirm
    weight: 2
    question: 이 문제를 어떤 방식으로 해결하나요?
    easier_questions:
      - question: 다른 곳과 비교해 이 사업만 다르게 하는 점 하나를 말해 주세요.
  - name: revenue_model
    label: 수익모델
    kind: ai_suggest
    weight: 2
    question: 어떻게 돈을 벌 계획인가요?
    options: [제품 판매, 구독, 수수료, 광고]
    easier_questions:
      - question: 고객이 돈을 내는 순간은 언제인가요?
  - name: resources
    label: 보유 자원·제약
    kind: ai_suggest
    weight: 1
    question: 지금 가진 자원(시간, 돈, 기술, 사람)과 제약은 무엇인가요?
    options: [혼자 운영, 초기 자금 적음, 제작 기술 보유, 주말에만 가능]
    multi_select: true
    easier_questions:
      - question: 일주일에 이 사업에 쓸 수 있는 시간은 얼마인가요?
  - name: validation_method
    label: 검증 방법
    kind: ai_suggest
    weight: 1
    question: 이 사업이 될지 먼저 확인해 볼 방법이 있나요?
    options: [지인에게 먼저 팔아보기, SNS로 반응 보기, 플리마켓 참가]
    easier_questions:
      - question: 처음 10명의 고객을 어디서 만날 수 있을까요?
rules:
  - 근거 없는 시장 규모를 사실처럼 제시하지 않는다
  - 임의의 매출 전망을 만들지 않는다
  - 확인하지 않은 경쟁사를 사실처럼 제시하지 않는다
```

`backend/app/harness/tasks/business_plan/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
{% block task_guidance %}
## 사업계획 지침
- 고객 문제 → 목표 고객 → 해결 방식 → 수익모델이 하나의 논리로 이어지게 쓴다.
- 위험은 사용자가 실제로 확인할 수 있는 형태로 적는다.
- 검증 계획은 이번 주에 바로 할 수 있는 작은 행동부터 제안한다.
- 카드는 진단 1~2개, 제안 2~3개, 실행 과제 2~3개로 구성한다.
{% endblock %}
```

`backend/app/harness/tasks/business_plan/evals/basic.yaml`:
```yaml
name: 향초 온라인 판매 기본 흐름
raw_input: 직접 만든 향초를 온라인으로 팔고 싶어요
answers:
  customer_problem:
    - answer_type: dont_know
    - value: 선물용 향초를 고르기가 어렵다
  target_customer:
    - answer_type: option
      option_indexes: [0]
  solution:
    - value: 향과 용도를 고르면 맞춤 추천해 준다
```

- [ ] **Step 5: 상품기획(product_planning) 과제 작성**

`backend/app/harness/tasks/product_planning/harness.py`:
```python
"""상품기획 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import ProductPlanningContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = ProductPlanningContent
    validators = VALIDATORS
```

`backend/app/harness/tasks/product_planning/output_schema.py`:
```python
"""상품기획 결과물. 이 모델이 하네스 설계의 기준점이다."""
from pydantic import BaseModel, Field


class ProductPlanningContent(BaseModel):
    value_proposition: str = Field(description="고객 문제를 해결하는 가치제안")
    core_features: list[str] = Field(description="핵심 기능 또는 구성")
    mvp_scope: str = Field(description="가장 작게 시작할 MVP 범위")
    price_direction: str = Field(description="가격 방향과 확인할 기준")
    validation_experiments: list[str] = Field(description="상품 가설을 검증할 실험")
```

`backend/app/harness/tasks/product_planning/validators.py`:
```python
"""상품기획 전용 검증 규칙(설계서 7.2 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator

MAX_CORE_FEATURES = 5


def check_mvp_not_too_big(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    features = result.content.get("core_features", [])
    if len(features) <= MAX_CORE_FEATURES:
        return []
    return [
        ValidationIssue(
            rule="mvp_too_big",
            message=f"핵심 기능이 {len(features)}개입니다. MVP는 {MAX_CORE_FEATURES}개 이하로 줄여 보세요.",
        )
    ]


VALIDATORS: list[Validator] = [check_mvp_not_too_big]
```

`backend/app/harness/tasks/product_planning/policy.yaml`:
```yaml
task_type: product_planning
title: 상품기획
description: 고객 문제를 해결하는 상품과 MVP를 정의합니다.
input_placeholder: 예) 집들이 선물용 수제 향초
input_examples:
  - 집들이 선물용 수제 향초
  - 반려견 이름을 새긴 가죽 목걸이
raw_input_field: product_idea
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
max_easier_level: 4
fields:
  - name: product_idea
    label: 상품 아이디어
    kind: must_confirm
    weight: 3
    question: 어떤 상품을 만들고 싶으신가요?
    easier_questions:
      - question: 지금 만들고 있거나 만들 수 있는 물건을 하나만 말해 주세요.
      - question: 아래 중 가장 가까운 걸 골라 주세요.
        options: [향초·디퓨저, 액세서리, 문구·굿즈, 의류·패브릭]
  - name: user
    label: 사용자
    kind: must_confirm
    weight: 3
    question: 이 상품을 주로 쓰는 사람은 누구인가요?
    options: [20~30대 1인 가구, 선물을 사는 사람, 아이를 키우는 부모, 반려동물 보호자]
    easier_questions:
      - question: 이 상품을 받으면 가장 좋아할 사람 한 명을 떠올려 보세요. 어떤 사람인가요?
      - question: 둘 중 더 가까운 쪽을 골라 주세요.
        options: [본인이 직접 쓰는 사람, 남에게 선물하는 사람]
  - name: usage_context
    label: 사용 상황
    kind: ai_suggest
    weight: 1
    question: 언제, 어디서 이 상품을 쓰나요?
    options: [집에서 쉴 때, 선물할 때, 출퇴근·이동 중, 특별한 날]
    easier_questions:
      - question: 이 상품이 가장 필요해지는 순간은 언제인가요?
  - name: customer_problem
    label: 고객 문제
    kind: must_confirm
    weight: 3
    question: 사용자가 지금 겪는 불편은 무엇인가요?
    easier_questions:
      - question: 이 상품이 없을 때 사용자는 무엇이 아쉬울까요?
      - question: 아래 중 가장 가까운 불편을 골라 주세요.
        options: [마음에 드는 디자인이 없다, 품질을 믿기 어렵다, 가격이 부담된다, 고르기가 어렵다]
  - name: core_value
    label: 핵심 가치
    kind: must_confirm
    weight: 2
    question: 이 상품이 다른 상품보다 나은 점 하나는 무엇인가요?
    easier_questions:
      - question: 친구에게 이 상품을 추천한다면 뭐라고 말하겠어요?
  - name: mvp
    label: MVP 구성
    kind: ai_suggest
    weight: 2
    question: 처음 판매할 때 꼭 들어가야 하는 구성은 무엇인가요?
    options: [단일 상품 1종, 용량·색상 2~3종, 선물 포장 포함, 맞춤 각인]
    multi_select: true
    easier_questions:
      - question: 딱 하나만 먼저 판다면 어떤 걸 팔겠어요?
  - name: production_constraints
    label: 제작 제약
    kind: ai_suggest
    weight: 1
    question: 제작할 때 제약이 있나요?
    options: [혼자 손으로 만든다, 하루 생산량이 적다, 재료비가 비싸다, 외주 제작이 필요하다]
    multi_select: true
    easier_questions:
      - question: 일주일에 몇 개까지 만들 수 있나요?
  - name: price_direction
    label: 가격 방향
    kind: ai_suggest
    weight: 1
    question: 어느 정도 가격대를 생각하나요?
    options: [1만원 이하, 1~3만원, 3~5만원, 5만원 이상]
    easier_questions:
      - question: 비슷한 상품을 산다면 얼마까지 내겠어요?
rules:
  - 고객 문제와 무관한 기능 확대를 제안하지 않는다
  - 제작 조건을 무시한 제안을 하지 않는다
  - MVP를 지나치게 크게 잡지 않는다
```

`backend/app/harness/tasks/product_planning/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
{% block task_guidance %}
## 상품기획 지침
- 가치제안은 확인된 고객 문제와 직접 연결한다.
- MVP는 제작 제약 안에서 가장 작게 시작할 수 있는 범위로 제안한다.
- 가격 방향은 숫자를 단정하지 말고, 사용자가 확인할 기준을 함께 준다.
- 카드는 진단 1~2개, 제안 2~3개, 실행 과제 2~3개로 구성한다.
{% endblock %}
```

`backend/app/harness/tasks/product_planning/evals/basic.yaml`:
```yaml
name: 수제 향초 기본 흐름
raw_input: 집들이 선물용 수제 향초
answers:
  user:
    - answer_type: option
      option_indexes: [1]
  customer_problem:
    - answer_type: dont_know
    - answer_type: dont_know
    - answer_type: option
      option_indexes: [3]
  core_value:
    - value: 집 분위기에 맞춰 향을 골라 준다
```

- [ ] **Step 6: 브랜딩(branding) 과제 작성**

`backend/app/harness/tasks/branding/harness.py`:
```python
"""브랜딩 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import BrandingContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = BrandingContent
    validators = VALIDATORS
```

`backend/app/harness/tasks/branding/output_schema.py`:
```python
"""브랜딩 결과물. 이 모델이 하네스 설계의 기준점이다."""
from pydantic import BaseModel, Field


class BrandingContent(BaseModel):
    positioning: str = Field(description="누구에게 어떤 점에서 다른 브랜드인지")
    brand_keywords: list[str] = Field(description="브랜드를 대표하는 키워드")
    tone_and_manner: str = Field(description="말투와 표현 방식")
    naming_directions: list[str] = Field(description="네이밍 방향 제안")
    slogan_directions: list[str] = Field(description="슬로건 방향 제안")
```

`backend/app/harness/tasks/branding/validators.py`:
```python
"""브랜딩 전용 검증 규칙(설계서 7.3 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator

DEFINITIVE_NAMING = ("이 이름으로 확정", "바로 사용하세요", "상표 문제 없음")


def check_naming_not_definitive(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    hits = [phrase for phrase in DEFINITIVE_NAMING if phrase in result.full_text]
    if not hits:
        return []
    return [
        ValidationIssue(
            rule="naming_not_definitive",
            message="상표·도메인 검토 전에 이름을 확정적으로 권고하는 표현이 있습니다.",
        )
    ]


VALIDATORS: list[Validator] = [check_naming_not_definitive]
```

`backend/app/harness/tasks/branding/policy.yaml`:
```yaml
task_type: branding
title: 브랜딩
description: 차별화된 정체성과 표현 체계를 세웁니다.
input_placeholder: 예) 30대 1인 가구를 위한 수제 향초
input_examples:
  - 30대 1인 가구를 위한 수제 향초
  - 반려견 보호자를 위한 가죽 소품
raw_input_field: product_and_customer
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
max_easier_level: 4
fields:
  - name: product_and_customer
    label: 상품과 고객
    kind: must_confirm
    weight: 3
    question: 어떤 상품을 누구에게 파나요?
    easier_questions:
      - question: 상품 이름과 그걸 살 사람을 한 줄로 말해 주세요.
  - name: customer_value
    label: 고객이 느낄 가치
    kind: must_confirm
    weight: 3
    question: 고객이 이 상품을 쓰고 어떤 기분이 들면 좋겠나요?
    easier_questions:
      - question: 고객이 후기에 써 줬으면 하는 한 문장은 무엇인가요?
      - question: 아래 중 가장 가까운 걸 골라 주세요.
        options: [편안하다, 특별하다, 믿을 수 있다, 재미있다]
  - name: differentiation
    label: 차별점
    kind: must_confirm
    weight: 3
    question: 비슷한 브랜드와 다른 점은 무엇인가요?
    easier_questions:
      - question: 다른 가게 대신 여기서 사야 하는 이유 하나를 말해 주세요.
  - name: desired_impression
    label: 원하는 인상
    kind: ai_suggest
    weight: 2
    question: 브랜드가 어떤 인상으로 보이면 좋겠나요?
    options: [따뜻한, 세련된, 자연스러운, 유쾌한, 고급스러운]
    multi_select: true
    easier_questions:
      - question: 이 브랜드를 사람으로 치면 어떤 사람일까요?
  - name: avoided_impression
    label: 피할 인상
    kind: ai_suggest
    weight: 1
    question: 피하고 싶은 인상이 있나요?
    options: [유치한, 차가운, 흔한, 비싸 보이는]
    multi_select: true
    easier_questions:
      - question: 이런 느낌만은 싫다 하는 브랜드가 있나요?
  - name: brand_personality
    label: 브랜드 성격
    kind: ai_suggest
    weight: 1
    question: 브랜드 성격에 가장 가까운 것은 무엇인가요?
    options: [다정한 친구, 믿음직한 전문가, 감각적인 예술가, 활발한 이웃]
    easier_questions:
      - question: 브랜드가 고객에게 말을 건다면 어떤 말투일까요?
  - name: tone_and_manner
    label: 톤앤매너
    kind: ai_suggest
    weight: 1
    question: 글과 이미지의 톤은 어떤 쪽이 좋을까요?
    options: [부드럽고 차분하게, 짧고 감각적으로, 친근하고 수다스럽게, 정돈되고 신뢰감 있게]
    easier_questions:
      - question: 좋아하는 브랜드의 SNS 말투를 하나 떠올려 보세요.
  - name: naming_slogan
    label: 네이밍·슬로건 방향
    kind: ai_suggest
    weight: 1
    question: 이름과 슬로건 중 무엇이 필요하나요?
    options: [이름부터 정하고 싶다, 슬로건부터 정하고 싶다, 둘 다 필요하다, 이미 이름이 있다]
    easier_questions:
      - question: 지금 가장 고민되는 건 이름인가요, 소개 문구인가요?
rules:
  - 흔한 감성 키워드를 나열하지 않는다
  - 상표·도메인 검토 없이 이름 사용을 확정적으로 권고하지 않는다
```

`backend/app/harness/tasks/branding/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
{% block task_guidance %}
## 브랜딩 지침
- 포지셔닝은 "누구에게, 무엇이, 왜 다른지"가 한 문장에 드러나게 쓴다.
- 키워드는 차별점과 고객 가치에서 뽑고, 어디에나 붙는 감성 단어는 피한다.
- 네이밍은 방향과 예시로만 제시하고 상표·도메인 확인을 실행 과제로 넣는다.
- 카드는 진단 1~2개, 제안 2~3개, 실행 과제 2~3개로 구성한다.
{% endblock %}
```

`backend/app/harness/tasks/branding/evals/basic.yaml`:
```yaml
name: 1인 가구 향초 브랜딩 기본 흐름
raw_input: 30대 1인 가구를 위한 수제 향초
answers:
  customer_value:
    - answer_type: dont_know
    - answer_type: dont_know
    - answer_type: option
      option_indexes: [0]
  differentiation:
    - answer_type: dont_know
    - value: 퇴근 시간대별로 향을 추천한다
```

- [ ] **Step 7: 마케팅 콘텐츠(marketing_content) 과제 작성**

`backend/app/harness/tasks/marketing_content/harness.py`:
```python
"""마케팅 콘텐츠 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import MarketingContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = MarketingContent
    validators = VALIDATORS
```

`backend/app/harness/tasks/marketing_content/output_schema.py`:
```python
"""마케팅 콘텐츠 결과물. 이 모델이 하네스 설계의 기준점이다."""
from typing import Literal

from pydantic import BaseModel, Field


class ContentPiece(BaseModel):
    format: Literal["sns_post", "ad_copy", "detail_page", "shortform_script"] = Field(
        description="콘텐츠 형식: SNS 글·광고 카피·상세페이지·숏폼 대본"
    )
    title: str = Field(description="콘텐츠 제목 또는 첫 문장")
    body: str = Field(description="콘텐츠 본문")


class MarketingContent(BaseModel):
    channel: str = Field(description="게시할 채널")
    key_message: str = Field(description="전달할 핵심 메시지")
    contents: list[ContentPiece] = Field(description="채널에 맞춘 콘텐츠")
    cta: str = Field(description="행동 유도 문구")
```

`backend/app/harness/tasks/marketing_content/validators.py`:
```python
"""마케팅 콘텐츠 전용 검증 규칙(설계서 7.4 금지·주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator

EXAGGERATIONS = ("100%", "무조건", "완벽한 효과", "최고의 효능")


def check_cta_present(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    if str(result.content.get("cta", "")).strip():
        return []
    return [ValidationIssue(rule="cta_present", message="행동 유도(CTA)가 없습니다.", severity="error")]


def check_no_exaggeration(
    state: SessionState, result: GenerationResult, policy: TaskPolicy
) -> list[ValidationIssue]:
    hits = [word for word in EXAGGERATIONS if word in result.full_text]
    if not hits:
        return []
    return [
        ValidationIssue(
            rule="no_exaggeration",
            message=f"과장 광고로 보일 수 있는 표현이 있습니다: {', '.join(hits)}",
        )
    ]


VALIDATORS: list[Validator] = [check_cta_present, check_no_exaggeration]
```

`backend/app/harness/tasks/marketing_content/policy.yaml`:
```yaml
task_type: marketing_content
title: 마케팅 콘텐츠
description: 채널과 목적에 맞는 실행 콘텐츠를 만듭니다.
input_placeholder: 예) 새로 나온 겨울 한정 향초를 알리고 싶어요
input_examples:
  - 새로 나온 겨울 한정 향초를 알리고 싶어요
  - 반려견 목걸이 각인 이벤트를 홍보하고 싶어요
raw_input_field: product
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
max_easier_level: 4
fields:
  - name: product
    label: 홍보 상품
    kind: must_confirm
    weight: 3
    question: 어떤 상품을 홍보하나요?
    easier_questions:
      - question: 이번에 알리고 싶은 상품 이름 하나만 말해 주세요.
  - name: target_customer
    label: 목표 고객
    kind: must_confirm
    weight: 3
    question: 이 콘텐츠를 누가 봤으면 하나요?
    options: [기존 구매 고객, 처음 보는 20~30대, 선물을 찾는 사람, 근처 지역 주민]
    easier_questions:
      - question: 이 글에 '좋아요'를 눌러 줬으면 하는 사람은 누구인가요?
      - question: 둘 중 더 가까운 쪽을 골라 주세요.
        options: [이미 아는 고객, 처음 만나는 고객]
  - name: content_goal
    label: 콘텐츠 목적
    kind: must_confirm
    weight: 3
    question: 이 콘텐츠로 무엇을 이루고 싶나요?
    options: [구매 유도, 브랜드 알리기, 이벤트 홍보, 신상품 출시 알림]
    easier_questions:
      - question: 이 글을 본 사람이 바로 해 줬으면 하는 행동은 무엇인가요?
  - name: channel
    label: 채널
    kind: must_confirm
    weight: 2
    question: 어디에 올릴 콘텐츠인가요?
    options: [인스타그램 피드, 인스타그램 릴스·숏폼, 스마트스토어 상세페이지, 블로그, 광고 문구]
    easier_questions:
      - question: 고객을 가장 자주 만나는 곳은 어디인가요?
  - name: key_message
    label: 핵심 메시지
    kind: ai_suggest
    weight: 2
    question: 꼭 전하고 싶은 한 마디는 무엇인가요?
    easier_questions:
      - question: 고객이 이 글을 보고 딱 하나만 기억한다면 무엇이면 좋겠나요?
  - name: evidence
    label: 근거
    kind: ai_suggest
    weight: 1
    question: 메시지를 믿게 할 근거가 있나요?
    options: [실제 고객 후기, 재료·제작 과정, 수상·인증, 판매 실적]
    multi_select: true
    easier_questions:
      - question: 고객에게 들었던 칭찬 중 기억나는 말이 있나요?
  - name: cta
    label: 행동 유도
    kind: ai_suggest
    weight: 1
    question: 보는 사람이 무엇을 하게 할까요?
    options: [구매하기, 프로필 링크 방문, 댓글·DM 문의, 저장·공유]
    easier_questions:
      - question: 글 마지막 문장에 어떤 부탁을 넣고 싶나요?
  - name: tone_length
    label: 톤·길이
    kind: default
    weight: 1
    default: 친근한 톤, 중간 길이
rules:
  - 확인되지 않은 효능을 쓰지 않는다
  - 과장 광고를 하지 않는다
  - 채널에 맞지 않는 형식을 쓰지 않는다
  - 행동 유도(CTA)를 빠뜨리지 않는다
```

`backend/app/harness/tasks/marketing_content/prompts/generate.md`:
```markdown
{% extends "_generate_base.md" %}
{% block task_guidance %}
## 마케팅 콘텐츠 지침
- 선택한 채널의 형식과 길이에 맞춘다(예: 릴스는 숏폼 대본, 상세페이지는 섹션 구성).
- 근거로 확인된 내용만 효능·성과로 쓰고, 없는 근거는 지어내지 않는다.
- 모든 콘텐츠는 행동 유도(CTA)로 끝낸다.
- 카드는 진단 1개, 제안(콘텐츠) 2~3개, 실행 과제 1~2개로 구성한다.
{% endblock %}
```

`backend/app/harness/tasks/marketing_content/evals/basic.yaml`:
```yaml
name: 겨울 한정 향초 홍보 기본 흐름
raw_input: 새로 나온 겨울 한정 향초를 알리고 싶어요
answers:
  target_customer:
    - answer_type: option
      option_indexes: [2]
  content_goal:
    - answer_type: option
      option_indexes: [3]
  channel:
    - answer_type: dont_know
    - value: 인스타그램 릴스
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_tasks.py -v`
Expected: 31 passed (등록부 1 + 정책 4 + 템플릿 20 + 시나리오 4 + 규칙 2)

- [ ] **Step 9: 전체 테스트 확인**

Run: `uv run --directory backend pytest`
Expected: 80 passed

- [ ] **Step 10: Commit**

```bash
git add backend/app/harness backend/tests/test_tasks.py
git commit -m "feat: 과제 4개 하네스 폴더와 등록부 추가"
```

---

### Task 7: API 계약과 라우터

**Files:**
- Create: `backend/app/schemas/__init__.py`(빈 파일), `backend/app/schemas/coaching.py`
- Create: `backend/app/api/__init__.py`(빈 파일), `backend/app/api/deps.py`, `backend/app/api/views.py`, `backend/app/api/coaching.py`
- Create: `backend/app/main.py`, `backend/scripts/export_openapi.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `HarnessRegistry`, `BaseHarness`(start, apply_answer, revise_answer, generate, asked_count, question_cap, policy), `SessionStore`, `InMemorySessionStore`, `get_provider`, `settings`, 오류들
- Produces:
  - `app.main.create_app(provider: LLMProvider | None = None, store: SessionStore | None = None, debug: bool | None = None) -> FastAPI`, 모듈 변수 `app`
  - 스키마 이름(프론트 타입에 그대로 나타남): `TaskSummary`, `TaskForm`, `ModeInfo`, `FieldSummary`, `CreateSessionRequest`, `AnswerRequest`, `ReviseAnswerRequest`, `Progress`, `SummaryItem`, `SessionView`, `ResultView`, `Question`, `QuestionOption`, `GenerationResult`, `ResultCard`, `ResultAssumption`, `ValidationReport`, `ValidationIssue`, `TraceEntry`
  - 엔드포인트(접두사 `/api/v1/coaching`): `GET /tasks`, `GET /tasks/{task_type}/form`, `POST /tasks/{task_type}/sessions`(201), `GET /sessions/{session_id}`, `POST /sessions/{session_id}/answers`, `PATCH /sessions/{session_id}/answers/{question_id}`, `POST /sessions/{session_id}/generate`, `GET /sessions/{session_id}/result`, `GET /sessions/{session_id}/trace`
  - 오류 응답 본문: `{"detail": "<한국어 메시지>"}` — 404(없는 과제·세션·결과), 422(하네스 규칙 위반·요청 형식), 502(AI 호출·생성 실패)
  - `scripts/export_openapi.py [출력 경로]`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_api.py`:
```python
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.providers.mock import MockProvider

BASE = "/api/v1/coaching"


@pytest.fixture
def client():
    return TestClient(create_app(provider=MockProvider(), debug=True))


def create_session(client, task_type="product_planning", raw_input="수제 향초"):
    response = client.post(f"{BASE}/tasks/{task_type}/sessions", json={"raw_input": raw_input})
    assert response.status_code == 201, response.text
    return response.json()


def test_list_tasks(client):
    response = client.get(f"{BASE}/tasks")
    assert response.status_code == 200
    assert [t["task_type"] for t in response.json()] == [
        "business_plan",
        "product_planning",
        "branding",
        "marketing_content",
    ]


def test_task_form(client):
    form = client.get(f"{BASE}/tasks/product_planning/form").json()
    assert form["title"] == "상품기획"
    assert {m["mode"]: m["question_cap"] for m in form["modes"]} == {
        "quick": 3,
        "standard": 5,
        "precise": 10,
    }
    assert form["fields"][0] == {"name": "product_idea", "label": "상품 아이디어", "kind": "must_confirm"}
    assert "rules" not in form


def test_unknown_task_and_session_404(client):
    assert client.get(f"{BASE}/tasks/nope/form").status_code == 404
    assert client.post(f"{BASE}/tasks/nope/sessions", json={"raw_input": "x"}).status_code == 404
    assert client.get(f"{BASE}/sessions/sess_없음").status_code == 404


def test_create_session_returns_first_question(client):
    view = create_session(client)
    assert view["status"] == "clarifying"
    assert view["next_question"]["field"] == "user"
    assert view["progress"] == {"asked": 0, "cap": 5, "readiness": view["progress"]["readiness"]}
    assert view["summary"][0]["field"] == "product_idea"
    assert view["summary"][0]["source"] == "user_free_text"
    assert view["can_generate"] is True
    assert "trace" not in view


def test_full_flow(client):
    view = create_session(client)
    sid = view["session_id"]

    first = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": first["question_id"], "answer_type": "option", "option_ids": ["o1"]},
    ).json()
    assert view["next_question"]["field"] == "usage_context"
    assert view["progress"]["asked"] == 1

    q = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": q["question_id"], "answer_type": "dont_know"}
    ).json()
    assert view["next_question"]["field"] == "usage_context"
    assert view["next_question"]["level"] == 1

    q = view["next_question"]
    view = client.post(
        f"{BASE}/sessions/{sid}/answers",
        json={"question_id": q["question_id"], "answer_type": "free_text", "value": "집들이 갈 때"},
    ).json()

    revised = client.patch(
        f"{BASE}/sessions/{sid}/answers/{first['question_id']}",
        json={"answer_type": "free_text", "value": "집들이 가는 30대"},
    )
    assert revised.status_code == 200
    assert any(i["value"] == "집들이 가는 30대" for i in revised.json()["summary"])

    result = client.post(f"{BASE}/sessions/{sid}/generate")
    assert result.status_code == 200
    body = result.json()
    assert body["status"] == "completed"
    assert body["result"]["cards"]
    assert body["validation"]["passed"] is True

    assert client.get(f"{BASE}/sessions/{sid}/result").json()["result"] == body["result"]
    trace = client.get(f"{BASE}/sessions/{sid}/trace").json()
    assert [t["stage"] for t in trace][0] == "diagnose"


def test_harness_errors_are_422(client):
    sid = create_session(client)["session_id"]
    response = client.post(
        f"{BASE}/sessions/{sid}/answers", json={"question_id": "q_엉뚱", "answer_type": "skip"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "지금 답할 수 있는 질문이 아닙니다."


def test_result_before_generate_is_404(client):
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/result").status_code == 404


def test_generate_failure_is_502_and_session_preserved():
    client = TestClient(create_app(provider=MockProvider(fail_stages={"generate"}), debug=True))
    sid = create_session(client)["session_id"]

    response = client.post(f"{BASE}/sessions/{sid}/generate")
    assert response.status_code == 502
    assert "다시 시도" in response.json()["detail"]

    view = client.get(f"{BASE}/sessions/{sid}").json()
    assert view["status"] == "failed"
    assert view["error"]
    assert view["summary"][0]["value"] == "수제 향초"


def test_trace_hidden_without_debug():
    client = TestClient(create_app(provider=MockProvider(), debug=False))
    sid = create_session(client)["session_id"]
    assert client.get(f"{BASE}/sessions/{sid}/trace").status_code == 404


def test_openapi_has_contract_schemas(client):
    spec = client.get("/openapi.json").json()
    assert f"{BASE}/sessions/{{session_id}}/answers/{{question_id}}" in spec["paths"]
    for name in ("SessionView", "ResultView", "Question", "AnswerRequest", "TaskForm"):
        assert name in spec["components"]["schemas"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `uv run --directory backend pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: API 스키마 구현**

`backend/app/schemas/coaching.py`:
```python
"""API 요청·응답 계약. 프론트 타입(frontend/src/api/schema.d.ts)은 이 파일에서 생성된다.

내부 세션 상태(trace, 프롬프트, 정책 규칙)는 여기에 싣지 않는다.
"""
from typing import Literal

from pydantic import BaseModel, Field

from app.core.results import GenerationResult, ValidationReport
from app.core.state import AnswerType, CoachingMode, InfoSource, Question, SessionStatus
from app.harness.policy import FieldKind


class TaskSummary(BaseModel):
    task_type: str
    title: str
    description: str


class ModeInfo(BaseModel):
    mode: CoachingMode
    question_cap: int


class FieldSummary(BaseModel):
    name: str
    label: str
    kind: FieldKind


class TaskForm(BaseModel):
    task_type: str
    title: str
    description: str
    input_placeholder: str
    input_examples: list[str]
    modes: list[ModeInfo]
    fields: list[FieldSummary]


class CreateSessionRequest(BaseModel):
    raw_input: str = Field(min_length=1, max_length=2000)
    mode: CoachingMode = CoachingMode.STANDARD


class AnswerRequest(BaseModel):
    question_id: str
    answer_type: AnswerType
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class ReviseAnswerRequest(BaseModel):
    answer_type: Literal[AnswerType.OPTION, AnswerType.FREE_TEXT]
    value: str | None = None
    option_ids: list[str] = Field(default_factory=list)


class Progress(BaseModel):
    asked: int
    cap: int
    readiness: float


class SummaryItem(BaseModel):
    field: str
    label: str
    value: str
    source: InfoSource
    confidence: float
    is_assumption: bool


class SessionView(BaseModel):
    session_id: str
    task_type: str
    mode: CoachingMode
    status: SessionStatus
    next_question: Question | None
    progress: Progress
    summary: list[SummaryItem]
    unknowns: list[str]
    can_generate: bool
    result_stale: bool
    error: str | None


class ResultView(BaseModel):
    session_id: str
    status: SessionStatus
    result: GenerationResult
    validation: ValidationReport | None
    stale: bool
```

- [ ] **Step 4: 의존성·뷰 변환 구현**

`backend/app/api/deps.py`:
```python
from typing import Annotated

from fastapi import Depends, Request

from app.core.store import SessionStore
from app.harness.registry import HarnessRegistry


def get_registry(request: Request) -> HarnessRegistry:
    return request.app.state.registry


def get_store(request: Request) -> SessionStore:
    return request.app.state.store


Registry = Annotated[HarnessRegistry, Depends(get_registry)]
Store = Annotated[SessionStore, Depends(get_store)]
```

`backend/app/api/views.py`:
```python
"""내부 상태 → API 응답 변환. 프론트가 바로 그릴 수 있는 값만 담는다."""
from app.core.state import CoachingMode, SessionState, SessionStatus
from app.harness.base import BaseHarness
from app.schemas.coaching import (
    FieldSummary,
    ModeInfo,
    Progress,
    ResultView,
    SessionView,
    SummaryItem,
    TaskForm,
    TaskSummary,
)


def to_task_summary(harness: BaseHarness) -> TaskSummary:
    policy = harness.policy
    return TaskSummary(task_type=policy.task_type, title=policy.title, description=policy.description)


def to_task_form(harness: BaseHarness) -> TaskForm:
    policy = harness.policy
    return TaskForm(
        task_type=policy.task_type,
        title=policy.title,
        description=policy.description,
        input_placeholder=policy.input_placeholder,
        input_examples=policy.input_examples,
        modes=[ModeInfo(mode=m, question_cap=policy.question_caps[m]) for m in CoachingMode],
        fields=[FieldSummary(name=f.name, label=f.label, kind=f.kind) for f in policy.fields],
    )


def to_session_view(state: SessionState, harness: BaseHarness) -> SessionView:
    summary: list[SummaryItem] = []
    for f in harness.policy.fields:
        item = state.facts.get(f.name) or state.assumptions.get(f.name)
        if item is None:
            continue
        summary.append(
            SummaryItem(
                field=f.name,
                label=f.label,
                value=item.value,
                source=item.source,
                confidence=item.confidence,
                is_assumption=f.name not in state.facts,
            )
        )
    return SessionView(
        session_id=state.session_id,
        task_type=state.task_type,
        mode=state.mode,
        status=state.status,
        next_question=state.pending_question,
        progress=Progress(
            asked=harness.asked_count(state),
            cap=harness.question_cap(state),
            readiness=state.readiness,
        ),
        summary=summary,
        unknowns=state.unknowns,
        can_generate=state.status is not SessionStatus.GENERATING,
        result_stale=state.result_stale,
        error=state.error,
    )


def to_result_view(state: SessionState) -> ResultView:
    assert state.result is not None
    return ResultView(
        session_id=state.session_id,
        status=state.status,
        result=state.result,
        validation=state.validation,
        stale=state.result_stale,
    )
```

`progress.asked`는 지금 걸려 있는 질문을 세지 않는다(답한 기본 질문 수). 테스트 `test_create_session_returns_first_question`이 `asked == 0`을 확인한다.

- [ ] **Step 5: 라우터와 앱 구현**

`backend/app/api/coaching.py`:
```python
"""코칭 API. 설계서 10.1 엔드포인트 + 이전 답변 수정 + 세션 조회 + 디버그 trace."""
from fastapi import APIRouter, HTTPException, Request

from app.api.deps import Registry, Store
from app.api.views import to_result_view, to_session_view, to_task_form, to_task_summary
from app.core.state import Answer, SessionState, TraceEntry
from app.harness.base import BaseHarness
from app.harness.errors import GenerationFailed, UnknownTaskError
from app.schemas.coaching import (
    AnswerRequest,
    CreateSessionRequest,
    ResultView,
    ReviseAnswerRequest,
    SessionView,
    TaskForm,
    TaskSummary,
)

router = APIRouter(prefix="/api/v1/coaching", tags=["coaching"])


def _harness(registry: Registry, task_type: str) -> BaseHarness:
    try:
        return registry.get(task_type)
    except UnknownTaskError:
        raise HTTPException(status_code=404, detail=f"없는 과제입니다: {task_type}") from None


def _load(registry: Registry, store: Store, session_id: str) -> tuple[SessionState, BaseHarness]:
    state = store.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return state, _harness(registry, state.task_type)


@router.get("/tasks", response_model=list[TaskSummary])
def list_tasks(registry: Registry) -> list[TaskSummary]:
    return [to_task_summary(h) for h in registry.all()]


@router.get("/tasks/{task_type}/form", response_model=TaskForm)
def get_task_form(task_type: str, registry: Registry) -> TaskForm:
    return to_task_form(_harness(registry, task_type))


@router.post("/tasks/{task_type}/sessions", response_model=SessionView, status_code=201)
def create_session(
    task_type: str, body: CreateSessionRequest, registry: Registry, store: Store
) -> SessionView:
    harness = _harness(registry, task_type)
    state = harness.start(body.raw_input, body.mode)
    store.save(state)
    return to_session_view(state, harness)


@router.get("/sessions/{session_id}", response_model=SessionView)
def get_session(session_id: str, registry: Registry, store: Store) -> SessionView:
    state, harness = _load(registry, store, session_id)
    return to_session_view(state, harness)


@router.post("/sessions/{session_id}/answers", response_model=SessionView)
def submit_answer(
    session_id: str, body: AnswerRequest, registry: Registry, store: Store
) -> SessionView:
    state, harness = _load(registry, store, session_id)
    harness.apply_answer(state, Answer(**body.model_dump()))
    store.save(state)
    return to_session_view(state, harness)


@router.patch("/sessions/{session_id}/answers/{question_id}", response_model=SessionView)
def revise_answer(
    session_id: str, question_id: str, body: ReviseAnswerRequest, registry: Registry, store: Store
) -> SessionView:
    state, harness = _load(registry, store, session_id)
    harness.revise_answer(state, Answer(question_id=question_id, **body.model_dump()))
    store.save(state)
    return to_session_view(state, harness)


@router.post("/sessions/{session_id}/generate", response_model=ResultView)
def generate(session_id: str, registry: Registry, store: Store) -> ResultView:
    state, harness = _load(registry, store, session_id)
    try:
        harness.generate(state)
    except GenerationFailed as exc:
        store.save(state)
        raise HTTPException(
            status_code=502,
            detail=f"결과를 만들지 못했습니다. 입력은 그대로 남아 있으니 다시 시도해 주세요. ({exc})",
        ) from None
    store.save(state)
    return to_result_view(state)


@router.get("/sessions/{session_id}/result", response_model=ResultView)
def get_result(session_id: str, registry: Registry, store: Store) -> ResultView:
    state, _ = _load(registry, store, session_id)
    if state.result is None:
        raise HTTPException(status_code=404, detail="아직 생성된 결과가 없습니다.")
    return to_result_view(state)


@router.get("/sessions/{session_id}/trace", response_model=list[TraceEntry])
def get_trace(session_id: str, request: Request, registry: Registry, store: Store) -> list[TraceEntry]:
    """하네스 튜닝용. DEBUG=true일 때만 열린다."""
    if not request.app.state.debug:
        raise HTTPException(status_code=404, detail="Not Found")
    state, _ = _load(registry, store, session_id)
    return state.trace
```

`backend/app/main.py`:
```python
"""FastAPI 앱. 실행: uv run --directory backend fastapi dev app/main.py"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import coaching
from app.config import settings
from app.core.store import InMemorySessionStore, SessionStore
from app.harness.errors import HarnessError
from app.harness.registry import HarnessRegistry
from app.providers.base import LLMProvider, ProviderError
from app.providers.factory import get_provider


def create_app(
    provider: LLMProvider | None = None,
    store: SessionStore | None = None,
    debug: bool | None = None,
) -> FastAPI:
    app = FastAPI(
        title="AX Coaching Platform API",
        version="0.1.0",
        separate_input_output_schemas=False,
    )
    app.state.registry = HarnessRegistry(provider or get_provider(settings.provider))
    app.state.store = store or InMemorySessionStore()
    app.state.debug = settings.debug if debug is None else debug
    app.include_router(coaching.router)

    @app.exception_handler(HarnessError)
    async def harness_error(request: Request, exc: HarnessError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    async def provider_error(request: Request, exc: ProviderError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content={"detail": f"AI 호출에 실패했습니다. 다시 시도해 주세요. ({exc})"},
        )

    return app


app = create_app()
```

`backend/scripts/export_openapi.py`:
```python
"""백엔드 OpenAPI 스키마를 파일로 내보낸다. 프론트 타입 생성(npm run gen:api)이 이 파일을 읽는다.

사용: uv run --directory backend python scripts/export_openapi.py <출력 경로>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
out.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OpenAPI 스키마를 저장했습니다: {out.resolve()}")
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run --directory backend pytest tests/test_api.py -v`
Expected: 10 passed

- [ ] **Step 7: 전체 테스트와 서버 기동 확인**

Run: `uv run --directory backend pytest`
Expected: 90 passed

Run (백그라운드): `uv run --directory backend fastapi dev app/main.py --port 8000`
Run: `curl -s http://localhost:8000/api/v1/coaching/tasks`
Expected: 과제 4개 JSON. 확인 후 서버를 끈다.

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/scripts backend/tests/test_api.py
git commit -m "feat: 코칭 API 계약과 라우터 추가"
```

---

### Task 8: 최소 React 프론트엔드

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`
- Create: `frontend/src/api/client.ts`, `frontend/src/api/types.ts`, `frontend/src/api/schema.d.ts`(생성물)
- Create: `frontend/src/components/QuestionCard.tsx`, `frontend/src/components/ResultPanel.tsx`

**Interfaces:**
- Consumes: Task 7의 OpenAPI 스키마(`scripts/export_openapi.py`), 엔드포인트와 스키마 이름
- Produces: `npm run gen:api`, `npm run build`, `npm run dev`(`/api` → `localhost:8000` 프록시). `src/api/client.ts`의 `api`(openapi-fetch 클라이언트)와 `errorMessage(error: unknown): string`, `src/api/types.ts`의 타입 별칭

- [ ] **Step 1: 프로젝트 파일 작성**

`frontend/package.json`:
```json
{
  "name": "ax-coaching-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "gen:api": "uv run --directory ../backend python scripts/export_openapi.py ../frontend/openapi.json && openapi-typescript openapi.json -o src/api/schema.d.ts"
  }
}
```

`frontend/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "types": ["vite/client"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/vite.config.ts`:
```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://localhost:8000" },
  },
});
```

`frontend/index.html`:
```html
<!doctype html>
<html lang="ko">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AX 코칭</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: 의존성 설치**

Run:
```bash
npm --prefix frontend install react react-dom openapi-fetch
npm --prefix frontend install -D vite @vitejs/plugin-react typescript @types/react @types/react-dom openapi-typescript
```
Expected: `frontend/node_modules`, `frontend/package-lock.json` 생성, package.json에 버전이 채워짐.

- [ ] **Step 3: API 타입 생성**

Run: `npm --prefix frontend run gen:api`
Expected: "OpenAPI 스키마를 저장했습니다" 출력, `frontend/src/api/schema.d.ts` 생성. 파일 안에 `"/api/v1/coaching/sessions/{session_id}/answers"`와 `SessionView`가 있어야 한다.

- [ ] **Step 4: API 클라이언트와 타입 별칭**

`frontend/src/api/client.ts`:
```ts
import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "/" });

export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";
}
```

`frontend/src/api/types.ts`:
```ts
import type { components } from "./schema";

type Schemas = components["schemas"];

export type TaskSummary = Schemas["TaskSummary"];
export type SessionView = Schemas["SessionView"];
export type ResultView = Schemas["ResultView"];
export type Question = Schemas["Question"];
export type AnswerRequest = Schemas["AnswerRequest"];
export type AnswerBody = Omit<AnswerRequest, "question_id">;
```

- [ ] **Step 5: 컴포넌트 작성**

`frontend/src/components/QuestionCard.tsx`:
```tsx
import { useEffect, useState } from "react";

import type { AnswerBody, Question } from "../api/types";

type Props = {
  question: Question;
  busy: boolean;
  onAnswer: (body: AnswerBody) => void;
};

export function QuestionCard({ question, busy, onAnswer }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [text, setText] = useState("");

  useEffect(() => {
    setSelected([]);
    setText("");
  }, [question.question_id]);

  function toggle(id: string) {
    if (!question.multi_select) {
      setSelected([id]);
      return;
    }
    setSelected((prev) => (prev.includes(id) ? prev.filter((v) => v !== id) : [...prev, id]));
  }

  const options = question.options ?? [];
  const level = question.level ?? 0;

  return (
    <section className="card">
      {level > 0 && (
        <p className="hint">
          {question.is_ai_proposal
            ? "AI가 추정한 후보예요. 가장 가까운 걸 고르거나 직접 고쳐 주세요."
            : "조금 더 쉽게 물어볼게요."}
        </p>
      )}
      <h2>{question.text}</h2>
      {question.multi_select && <p className="hint">여러 개 고를 수 있어요</p>}

      {options.length > 0 && (
        <div className="chips">
          {options.map((o) => (
            <button
              key={o.id}
              type="button"
              className={selected.includes(o.id) ? "chip on" : "chip"}
              onClick={() => toggle(o.id)}
            >
              {o.label}
              {o.ai_suggested && <span className="badge">AI 제안</span>}
            </button>
          ))}
        </div>
      )}
      {selected.length > 0 && (
        <button
          type="button"
          disabled={busy}
          onClick={() => onAnswer({ answer_type: "option", option_ids: selected })}
        >
          선택 완료
        </button>
      )}

      <textarea
        value={text}
        placeholder="직접 입력"
        onChange={(e) => setText(e.target.value)}
        rows={2}
      />
      <button
        type="button"
        disabled={busy || !text.trim()}
        onClick={() => onAnswer({ answer_type: "free_text", value: text })}
      >
        직접 입력으로 답하기
      </button>

      <div className="row">
        <button type="button" className="ghost" disabled={busy} onClick={() => onAnswer({ answer_type: "dont_know" })}>
          모르겠어요
        </button>
        <button type="button" className="ghost" disabled={busy} onClick={() => onAnswer({ answer_type: "skip" })}>
          건너뛰기
        </button>
      </div>
    </section>
  );
}
```

`frontend/src/components/ResultPanel.tsx`:
```tsx
import type { ResultView } from "../api/types";

const CARD_LABEL: Record<string, string> = {
  diagnosis: "진단",
  suggestion: "제안",
  action: "실행 과제",
};

export function ResultPanel({ view }: { view: ResultView }) {
  const { result, validation } = view;
  const cards = [...result.cards].sort((a, b) => a.order - b.order);
  const assumptions = result.assumptions ?? [];
  const issues = validation?.issues ?? [];

  return (
    <section>
      {cards.map((card) => (
        <article key={`${card.card_type}-${card.order}`} className="card">
          <p className="hint">{CARD_LABEL[card.card_type] ?? card.card_type}</p>
          <h3>{card.title}</h3>
          <p>{card.body}</p>
        </article>
      ))}

      {assumptions.length > 0 && (
        <article className="card">
          <h3>AI가 가정한 내용</h3>
          <ul>
            {assumptions.map((a) => (
              <li key={a.field}>
                {a.field}: {a.value}
                {a.requires_confirmation && " (확인 필요)"}
              </li>
            ))}
          </ul>
        </article>
      )}

      {issues.length > 0 && (
        <article className="card warn">
          <h3>검토가 필요한 부분</h3>
          <ul>
            {issues.map((i, idx) => (
              <li key={`${i.rule}-${idx}`}>{i.message}</li>
            ))}
          </ul>
        </article>
      )}

      <article className="card">
        <h3>완성본</h3>
        <pre className="full-text">{result.full_text}</pre>
        <button type="button" onClick={() => void navigator.clipboard.writeText(result.full_text)}>
          복사
        </button>
      </article>
    </section>
  );
}
```

- [ ] **Step 6: 앱 화면 작성**

`frontend/src/App.tsx`:
```tsx
import { useEffect, useState } from "react";

import { api, errorMessage } from "./api/client";
import type { AnswerBody, ResultView, SessionView, TaskSummary } from "./api/types";
import { QuestionCard } from "./components/QuestionCard";
import { ResultPanel } from "./components/ResultPanel";

const SOURCE_LABEL: Record<string, string> = {
  user_free_text: "직접 입력",
  user_selected_ai_option: "선택",
  previous_task: "이전 과제",
  ai_assumption: "AI 가정",
  default: "기본값",
};

type ApiResult<T> = { data?: T; error?: unknown };

export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [task, setTask] = useState<TaskSummary | null>(null);
  const [rawInput, setRawInput] = useState("");
  const [session, setSession] = useState<SessionView | null>(null);
  const [result, setResult] = useState<ResultView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run<T>(request: () => Promise<ApiResult<T>>, onData: (data: T) => void) {
    setBusy(true);
    setError(null);
    try {
      const { data, error } = await request();
      if (data !== undefined) onData(data);
      else setError(errorMessage(error));
    } catch {
      setError("서버에 연결하지 못했습니다. 백엔드가 켜져 있는지 확인해 주세요.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void run(() => api.GET("/api/v1/coaching/tasks"), (data) => setTasks(data));
  }, []);

  function startSession() {
    if (!task) return;
    void run(
      () =>
        api.POST("/api/v1/coaching/tasks/{task_type}/sessions", {
          params: { path: { task_type: task.task_type } },
          body: { raw_input: rawInput, mode: "standard" },
        }),
      (data) => setSession(data),
    );
  }

  function answer(body: AnswerBody) {
    if (!session?.next_question) return;
    const questionId = session.next_question.question_id;
    void run(
      () =>
        api.POST("/api/v1/coaching/sessions/{session_id}/answers", {
          params: { path: { session_id: session.session_id } },
          body: { ...body, question_id: questionId },
        }),
      (data) => setSession(data),
    );
  }

  function generate() {
    if (!session) return;
    void run(
      () =>
        api.POST("/api/v1/coaching/sessions/{session_id}/generate", {
          params: { path: { session_id: session.session_id } },
        }),
      (data) => setResult(data),
    );
  }

  function reset() {
    setTask(null);
    setRawInput("");
    setSession(null);
    setResult(null);
    setError(null);
  }

  return (
    <main>
      <header>
        <h1>AX 코칭</h1>
        {task && (
          <button type="button" className="ghost" onClick={reset}>
            처음으로
          </button>
        )}
      </header>

      {error && <p className="error">{error}</p>}

      {!task && (
        <section>
          <h2>어떤 코칭을 받을까요?</h2>
          {tasks.map((t) => (
            <button key={t.task_type} type="button" className="task" onClick={() => setTask(t)}>
              <strong>{t.title}</strong>
              <span>{t.description}</span>
            </button>
          ))}
        </section>
      )}

      {task && !session && (
        <section className="card">
          <h2>{task.title}</h2>
          <p className="hint">아이디어를 한 줄로 적어 주세요.</p>
          <textarea value={rawInput} onChange={(e) => setRawInput(e.target.value)} rows={3} />
          <button type="button" disabled={busy || !rawInput.trim()} onClick={startSession}>
            시작하기
          </button>
        </section>
      )}

      {session && !result && (
        <>
          <p className="progress">
            질문 {session.progress.asked}/{session.progress.cap} · 준비도{" "}
            {Math.round(session.progress.readiness * 100)}%
          </p>

          {session.next_question ? (
            <QuestionCard question={session.next_question} busy={busy} onAnswer={answer} />
          ) : (
            <p className="card">필요한 정보가 모였어요. 결과를 만들어 볼까요?</p>
          )}

          <section className="card">
            <h3>지금까지 확인된 정보</h3>
            <ul>
              {session.summary.map((item) => (
                <li key={item.field}>
                  {item.label}: {item.value}{" "}
                  <span className="badge">{SOURCE_LABEL[item.source] ?? item.source}</span>
                </li>
              ))}
            </ul>
          </section>

          <button type="button" className="primary" disabled={busy || !session.can_generate} onClick={generate}>
            {busy ? "처리 중…" : "이대로 결과 만들기"}
          </button>
        </>
      )}

      {result && <ResultPanel view={result} />}
    </main>
  );
}
```

`frontend/src/main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`frontend/src/styles.css`:
```css
/* 디자인 HTML을 받기 전까지 쓰는 최소 스타일. 디자인이 오면 통째로 교체한다. */
:root {
  font-family: system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  color: #1d1d1f;
  background: #f5f5f7;
}
body { margin: 0; }
main { max-width: 480px; margin: 0 auto; padding: 16px; }
header { display: flex; justify-content: space-between; align-items: center; }
h1 { font-size: 20px; }
h2 { font-size: 18px; }
h3 { font-size: 16px; margin: 0 0 8px; }
button {
  display: block; width: 100%; margin: 8px 0; padding: 12px;
  border: 1px solid #c7c7cc; border-radius: 10px; background: #fff; font-size: 15px; cursor: pointer;
}
button:disabled { opacity: 0.5; cursor: default; }
button.primary { background: #1d1d1f; color: #fff; border-color: #1d1d1f; }
button.ghost { background: transparent; }
header button.ghost { width: auto; }
button.task { text-align: left; }
button.task span { display: block; color: #6e6e73; font-size: 13px; margin-top: 4px; }
textarea { width: 100%; box-sizing: border-box; padding: 10px; border-radius: 10px; border: 1px solid #c7c7cc; font: inherit; }
.card { background: #fff; border-radius: 14px; padding: 16px; margin: 12px 0; }
.card.warn { border: 1px solid #ff9f0a; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { width: auto; margin: 0; padding: 8px 12px; border-radius: 999px; }
.chip.on { background: #1d1d1f; color: #fff; }
.row { display: flex; gap: 8px; }
.hint { color: #6e6e73; font-size: 13px; margin: 0 0 6px; }
.badge { margin-left: 6px; font-size: 11px; color: #6e6e73; }
.progress { color: #6e6e73; font-size: 13px; }
.error { background: #ffe5e5; color: #a1001b; padding: 12px; border-radius: 10px; }
.full-text { white-space: pre-wrap; font-family: inherit; }
```

- [ ] **Step 7: 빌드 확인**

Run: `npm --prefix frontend run build`
Expected: `tsc --noEmit` 오류 없음, `vite build`가 `frontend/dist/` 생성.

타입 오류가 나면 `schema.d.ts`의 실제 타입과 `types.ts`·컴포넌트를 맞춘다(`schema.d.ts`는 고치지 않는다).

- [ ] **Step 8: 개발 서버로 한 사이클 확인**

Run (백그라운드): `uv run --directory backend fastapi dev app/main.py --port 8000`
Run (백그라운드): `npm --prefix frontend run dev -- --port 5173 --strictPort`
Run: `curl -s http://localhost:5173/api/v1/coaching/tasks`
Expected: 프록시를 거쳐 과제 4개 JSON.

브라우저(Playwright)로 `http://localhost:5173` 열기 → 상품기획 → "수제 향초" 입력 → 시작하기 → 모르겠어요 한 번(쉬운 질문 안내가 보임) → 직접 입력으로 답하기 → "이대로 결과 만들기" → 결과 카드와 완성본이 보이는지 확인. 확인 후 두 서버를 끈다.

- [ ] **Step 9: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/src
git commit -m "feat: 계약 기반 최소 React 프론트엔드 추가"
```

---

### Task 9: CLAUDE.md와 최종 확인

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: 앞선 모든 Task의 구조·명령
- Produces: 이후 작업 세션이 읽는 프로젝트 규칙 문서

- [ ] **Step 1: `CLAUDE.md` 작성**

`CLAUDE.md`:
````markdown
# AX 코칭 플랫폼

창작자가 좋은 프롬프트를 쓰지 못해도 과제별 적응형 질문으로 생각을 구체화해 사업계획·상품기획·브랜딩·마케팅 콘텐츠 결과물로 바꾸도록 돕는 모바일 친화형 코칭 플랫폼. 학교 수업 팀 프로젝트다(개발 1명, 디자인 1명).

- 기획 근거: `docs/planning/` (기능 설계, 기획 및 하네스 설계서 — PDF와 추출 텍스트)
- 현재 설계: `docs/superpowers/specs/`
- **요구사항·디자인·하네스는 자주 바뀐다.** 바뀌었을 때 고칠 곳이 적은 쪽을 고른다.

## 실행

| 할 일 | 명령 (저장소 루트에서) |
|---|---|
| 백엔드 테스트 | `uv run --directory backend pytest` |
| 백엔드 서버 | `uv run --directory backend fastapi dev app/main.py` → http://localhost:8000/docs |
| 프론트 타입 재생성 | `npm --prefix frontend run gen:api` |
| 프론트 개발 서버 | `npm --prefix frontend run dev` → http://localhost:5173 (`/api`는 8000으로 프록시) |
| 프론트 빌드·타입 검사 | `npm --prefix frontend run build` |

## 구조

- `backend/app/harness/base.py` — 모든 과제가 공유하는 파이프라인. 단계 하나 = 메서드 하나.
- `backend/app/harness/tasks/<task>/` — 과제별 하네스 전부(결과물 스키마, 정책, 프롬프트, 검증, 시나리오).
- `backend/app/harness/prompts/` — 공통 프롬프트. 과제 폴더 `prompts/`에 같은 이름이 있으면 그게 우선.
- `backend/app/providers/` — 모델 제공자. 지금은 `MockProvider`만 있다.
- `backend/app/schemas/` — API 계약의 원본.
- `frontend/src/api/schema.d.ts` — 생성물. 손으로 고치지 않는다.
- `design/` — 디자인 HTML 원본. 고치지 않는다.

## 과제 하네스를 고칠 때

결과물에서 거꾸로 따라간다.

1. `output_schema.py` — 원하는 결과물이 바뀌었나?
2. `policy.yaml` — 그 결과물에 필요한 정보(필드·가중치·종류), 질문 문구와 순서, '모르겠어요' 사다리(`easier_questions`), 모드별 질문 상한, 준비도 기준, 금지 규칙
3. `prompts/` — 이 과제에서만 다르게 할 단계 템플릿 (`diagnose`, `easier_question`, `propose_value`, `generate`, `validate`)
4. `validators.py` — 결과를 기계적으로 확인할 규칙
5. `harness.py` — 위로 표현할 수 없는 로직만 `BaseHarness` 메서드를 오버라이드
6. `evals/*.yaml` — 바뀐 흐름을 시나리오로 남긴다

고친 뒤 `uv run --directory backend pytest`. `tests/test_tasks.py`가 정책·템플릿·시나리오·스키마가 서로 맞는지 확인한다. 하네스 동작을 볼 때는 `GET /api/v1/coaching/sessions/{id}/trace`(DEBUG=true)로 단계별 프롬프트와 응답을 본다.

새 과제를 추가할 때는 폴더를 만들고 `app/harness/registry.py`의 `TASK_TYPES`에 넣는다.

## 하네스 원칙 (설계서 2.2, 16장)

- 부족한 정보는 질문하고, 모호한 정보는 확인한다. 선택지는 제안일 뿐이며 직접 입력을 항상 허용한다.
- '모르겠어요'는 포기가 아니라 질문이 어렵다는 신호다. 같은 필드를 더 쉽게 물어 답을 얻을 때까지 머문다(policy 사다리 → LLM 쉬운 질문 → AI 후보 제안). 빠져나가는 길은 답하기·건너뛰기·결과 만들기뿐이다.
- AI가 보완한 정보는 가정(`assumptions`)으로 두고 사실(`facts`)과 섞지 않는다. 모든 정보에 출처를 남긴다.
- 사용자는 언제든 현재 정보로 결과를 만들 수 있다.
- 시스템 프롬프트와 정책은 프론트로 내보내지 않는다.

## API 계약이 바뀔 때

1. `backend/app/schemas/`(또는 `app/core/`의 응답 모델)를 고친다.
2. `uv run --directory backend pytest`
3. `npm --prefix frontend run gen:api` → `npm --prefix frontend run build`에서 나는 타입 오류를 따라 프론트를 고친다.

## 디자인 HTML을 받았을 때

`design/README.md`의 절차를 따른다. 원본은 날짜 폴더에 그대로 두고, 직전 버전과 diff해 바뀐 화면만 React에 반영한다. 디자인 때문에 API가 바뀌어야 하면 위 "API 계약이 바뀔 때"를 먼저 한다.

## 비용

학교 수업이라 LLM 비용을 아낀다. 개발·테스트는 `MockProvider`(`PROVIDER=mock`)로 한다. 실제 모델 어댑터를 추가할 때는 `app/providers/`에 `LLMProvider`를 구현하고 `factory.py`에 등록한다. 테스트는 계속 Mock으로 돌아야 한다. `policy.llm_validation`은 생성마다 호출이 하나 늘어나므로 기본으로 끈다.
````

- [ ] **Step 2: 최종 확인**

Run: `uv run --directory backend pytest`
Expected: 90 passed

Run: `npm --prefix frontend run gen:api` 후 `git status --short frontend/src/api/schema.d.ts`
Expected: 변경 없음(타입이 계약과 일치).

Run: `npm --prefix frontend run build`
Expected: 성공

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: 프로젝트 CLAUDE.md 추가"
```
