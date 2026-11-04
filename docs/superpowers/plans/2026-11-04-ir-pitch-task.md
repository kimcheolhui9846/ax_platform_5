# IR 피치덱 과제 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 다섯 번째 과제 `ir_pitch`(IR 피치덱 원고)를 추가해, 창작자가 적응형 질문에 답하면 투자자 발표용 슬라이드별 원고가 나오게 한다.

**Architecture:** 기존 과제와 같은 하네스 구조를 그대로 쓴다. 과제 폴더 `backend/app/harness/tasks/ir_pitch/`(결과 스키마·정책·생성 지침·검증·시나리오)를 만들고 `TASK_TYPES` 끝에 등록한다. 공통 파이프라인(`base.py`)·API·프론트 로직은 바꾸지 않는다. 프론트는 과제 목록을 API에서 받으므로 미리보기 픽스처와 문구만 고친다.

**Tech Stack:** Python 3.12, Pydantic v2, Jinja2 템플릿, pytest / React 19, vitest

## Global Constraints

- 과제 이름(내부): `ir_pitch`. 화면 제목: `IR 피치덱`. 등록 순서는 `TASK_TYPES`의 **맨 끝**(기존 이어가기 순서 사업계획→상품기획→브랜딩→마케팅을 깨지 않는다. 마케팅 다음이 IR, IR 다음은 처음으로 돌아간다).
- API 계약(스키마) 변경 없음. `task_type`은 이미 `str`이다. `gen:api` 불필요.
- 테스트는 모두 Mock(`MockProvider`)으로 돈다. 실제 AI 호출 없음.
- 정책 YAML은 모르는 키를 거부한다. 키는 `app/harness/policy.py`의 `TaskPolicy`·`FieldPolicy`에 있는 것만 쓴다.
- 템플릿에 세션 값은 `| inline`·`| block`으로만 넣는다(이번 과제 템플릿은 정적 지침만 담아 세션 값을 넣지 않는다).
- 커밋 메시지에 AI 공동저자·생성 표기를 넣지 않는다.
- 각 Task 끝에 `uv run --directory backend pytest`(전체)가 통과해야 한다(프론트 Task는 `npm --prefix frontend test`와 `npm --prefix frontend run build`).

## 결정 사항

- **결과물은 피치덱 원고**(슬라이드마다 제목 문장·발표 원고). 사업계획서와 겹치지 않게 "투자자를 설득하는 흐름"에 초점을 둔다. 디자인된 슬라이드 파일(.pptx)은 만들지 않는다(문서 내려받기로 PDF·Word·HTML).
- 슬라이드 종류는 10개 고정 목록(`SlideType`)에서 고른다. 문제·해결·투자 요청 슬라이드가 빠지면 경고(오류가 아님 — 짧은 덱도 허용).
- 투자 요청(`ask`)이 비면 오류(마케팅의 CTA와 같은 성격).
- 근거 없는 시장 규모·기업가치·매출 전망은 경고(사업계획과 같은 원칙).
- 희망 투자 금액·현재 매출은 보완 항목이고 처음부터 AI에 보내지 않는다(`private_fields`).
- 이미지 생성은 끈다(비용), 근거 자료(`evidence.yaml`)는 두지 않는다(검토 없음).
- 이어가기: 사업계획·상품기획·브랜딩·마케팅의 아이디어·고객·문제·수익 필드를 IR 필드로 받는다. `solution`은 사업계획과 이름이 같아 자동으로 온다.

## File Structure

- Create `backend/app/harness/tasks/ir_pitch/__init__.py` — 빈 파일(패키지)
- Create `backend/app/harness/tasks/ir_pitch/output_schema.py` — `SlideType`, `PitchSlide`, `IrPitchContent`
- Create `backend/app/harness/tasks/ir_pitch/validators.py` — `check_ask_present`, `check_core_slides`, `check_unsupported_investor_claims`, `VALIDATORS`
- Create `backend/app/harness/tasks/ir_pitch/harness.py` — `Harness(BaseHarness)`
- Create `backend/app/harness/tasks/ir_pitch/policy.yaml` — 필드·질문·사다리·보완 항목·이어가기·규칙
- Create `backend/app/harness/tasks/ir_pitch/prompts/generate.md` — IR 생성 지침
- Create `backend/app/harness/tasks/ir_pitch/evals/basic.yaml`, `evals/quick-skip.yaml` — 시나리오
- Create `backend/tests/test_ir_pitch.py` — IR 전용 테스트(검증 규칙·정책·흐름·이어가기)
- Modify `backend/app/harness/registry.py` — `TASK_TYPES`에 `"ir_pitch"`
- Modify `scripts/measure_parallel.yaml` — `ir_pitch` 조각(측정 전용)
- Modify `backend/tests/test_api.py`, `test_evidence.py`, `test_images.py`, `test_tasks.py` — 과제 목록을 열거하는 기대값에 `ir_pitch`
- Modify `frontend/src/preview/fixtures.ts` — `TASKS`에 IR 카드
- Modify `frontend/src/screens/HomeScreen.tsx` — 주석·안내 문구의 "네 개"
- Modify `frontend/src/styles/screens.css` — 홈 카드가 홀수일 때 마지막 카드가 두 칸을 차지
- Modify docs(컨트롤러가 마지막에): `README.md`, `docs/DEMO.md`, `docs/DEPLOY.md`, `docs/HANDOFF.md`, `docs/WBS.xlsx`

---

### Task 1: IR 결과 스키마와 검증 규칙

**Files:**
- Create: `backend/app/harness/tasks/ir_pitch/__init__.py`
- Create: `backend/app/harness/tasks/ir_pitch/output_schema.py`
- Create: `backend/app/harness/tasks/ir_pitch/validators.py`
- Test: `backend/tests/test_ir_pitch.py`

**Interfaces:**
- Consumes: `app.harness.validation.term_rule(rule, terms, message_template) -> Validator`, `app.core.results.GenerationResult, ValidationIssue, ResultCard, sections_from_cards`, `app.core.state.SessionState`, `app.harness.policy.TaskPolicy`
- Produces:
  - `output_schema.SlideType = Literal["cover","problem","solution","market","business_model","traction","competition","team","financials","ask"]`
  - `output_schema.PitchSlide(slide_type: SlideType, headline: str, script: str)`
  - `output_schema.IrPitchContent(one_liner: str, slides: list[PitchSlide] (5~12개), ask: str, investor_questions: list[str])`
  - `validators.CORE_SLIDES = ("problem", "solution", "ask")`
  - `validators.check_ask_present(state, result, policy) -> list[ValidationIssue]` (rule `ask_present`, severity `error`)
  - `validators.check_core_slides(state, result, policy) -> list[ValidationIssue]` (rule `core_slides`, 경고)
  - `validators.check_unsupported_investor_claims` (rule `unsupported_investor_claims`, `term_rule`)
  - `validators.VALIDATORS: list[Validator]` (위 세 개, 이 순서)

- [ ] **Step 1: Write the failing test**

`backend/tests/test_ir_pitch.py`:

```python
"""IR 피치덱 과제: 결과 스키마와 과제 전용 검증 규칙."""
import pytest
from pydantic import ValidationError

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.tasks.ir_pitch.output_schema import IrPitchContent
from app.harness.tasks.ir_pitch.validators import (
    VALIDATORS,
    check_ask_present,
    check_core_slides,
    check_unsupported_investor_claims,
)

POLICY = TaskPolicy(task_type="ir_pitch", title="IR 피치덱", heading="h", deliverable="d", fields=[])
STATE = SessionState(task_type="ir_pitch")


def slide(slide_type: str) -> dict:
    return {"slide_type": slide_type, "headline": "제목 문장", "script": "발표 원고"}


def content(types=("cover", "problem", "solution", "market", "ask"), ask="시드 3억 원, 제작 설비") -> dict:
    return {
        "one_liner": "한글 디자인 굿즈 브랜드",
        "slides": [slide(t) for t in types],
        "ask": ask,
        "investor_questions": ["재구매율은 얼마인가요?"],
    }


def result(content_value: dict, full_text: str = "본문") -> GenerationResult:
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    return GenerationResult(sections=sections_from_cards([card]), full_text=full_text, content=content_value)


def test_content_requires_five_to_twelve_slides():
    IrPitchContent.model_validate(content())
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("cover", "problem", "ask")))
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("problem",) * 13))


def test_content_rejects_unknown_slide_type():
    with pytest.raises(ValidationError):
        IrPitchContent.model_validate(content(types=("cover", "problem", "solution", "ask", "appendix")))


def test_missing_ask_is_an_error():
    assert check_ask_present(STATE, result(content()), POLICY) == []
    issues = check_ask_present(STATE, result(content(ask="  ")), POLICY)
    assert [(i.rule, i.severity) for i in issues] == [("ask_present", "error")]


def test_missing_core_slides_is_a_warning_naming_them():
    assert check_core_slides(STATE, result(content()), POLICY) == []
    issues = check_core_slides(STATE, result(content(types=("cover", "market", "team", "traction", "financials"))), POLICY)
    assert [(i.rule, i.severity) for i in issues] == [("core_slides", "warning")]
    assert "문제" in issues[0].message and "해결" in issues[0].message and "투자 요청" in issues[0].message


def test_unsupported_investor_claims_are_flagged():
    assert check_unsupported_investor_claims(STATE, result(content(), "기업가치 100억 원, TAM 1조"), POLICY)
    assert not check_unsupported_investor_claims(STATE, result(content(), "인터뷰 20명 진행"), POLICY)


def test_validators_are_registered_in_order():
    assert VALIDATORS == [check_ask_present, check_core_slides, check_unsupported_investor_claims]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory backend pytest tests/test_ir_pitch.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'app.harness.tasks.ir_pitch'`)

- [ ] **Step 3: Write minimal implementation**

`backend/app/harness/tasks/ir_pitch/__init__.py`: 빈 파일.

`backend/app/harness/tasks/ir_pitch/output_schema.py`:

```python
"""IR 피치덱 결과물. 이 모델이 하네스 설계의 기준점이다(필드 → 질문 → 검증이 여기서 파생)."""
from typing import Literal

from pydantic import BaseModel, Field

SlideType = Literal[
    "cover", "problem", "solution", "market", "business_model", "traction", "competition", "team", "financials", "ask"
]


class PitchSlide(BaseModel):
    slide_type: SlideType = Field(
        description="슬라이드 종류: 표지·문제·해결·시장·비즈니스 모델·성과·경쟁·팀·재무 계획·투자 요청"
    )
    headline: str = Field(description="슬라이드 한 장의 핵심 주장 한 문장")
    script: str = Field(description="이 슬라이드에서 발표자가 말할 원고")


class IrPitchContent(BaseModel):
    one_liner: str = Field(description="투자자에게 회사를 한 문장으로 소개")
    slides: list[PitchSlide] = Field(min_length=5, max_length=12, description="발표 순서대로 놓은 슬라이드")
    ask: str = Field(description="투자 요청: 원하는 투자 형태와 자금 사용 계획")
    investor_questions: list[str] = Field(description="투자자가 물을 만한 질문과 답을 준비할 것")
```

`backend/app/harness/tasks/ir_pitch/validators.py`:

```python
"""IR 피치덱 전용 검증 규칙(투자 요청 필수, 핵심 슬라이드, 근거 없는 수치 주의)."""
from app.core.results import GenerationResult, ValidationIssue
from app.core.state import SessionState
from app.harness.policy import TaskPolicy
from app.harness.validation import Validator, term_rule

CORE_SLIDES = ("problem", "solution", "ask")
SLIDE_LABELS = {"problem": "문제", "solution": "해결", "ask": "투자 요청"}
UNSUPPORTED_CLAIMS = ("기업가치", "밸류에이션", "시장 규모", "TAM", "예상 매출", "매출 전망")


def check_ask_present(state: SessionState, result: GenerationResult, policy: TaskPolicy) -> list[ValidationIssue]:
    if str(result.content.get("ask", "")).strip():
        return []
    return [ValidationIssue(rule="ask_present", message="투자 요청(금액·용도)이 없습니다.", severity="error")]


def check_core_slides(state: SessionState, result: GenerationResult, policy: TaskPolicy) -> list[ValidationIssue]:
    present = {s.get("slide_type") for s in result.content.get("slides", [])}
    missing = [SLIDE_LABELS[t] for t in CORE_SLIDES if t not in present]
    if not missing:
        return []
    return [ValidationIssue(rule="core_slides", message=f"핵심 슬라이드가 빠졌습니다: {', '.join(missing)}")]


check_unsupported_investor_claims = term_rule(
    "unsupported_investor_claims",
    UNSUPPORTED_CLAIMS,
    "근거 확인이 필요한 표현이 있습니다: {terms}. 출처가 없다면 가정으로 표시하세요.",
)


VALIDATORS: list[Validator] = [check_ask_present, check_core_slides, check_unsupported_investor_claims]
```

(`ValidationIssue`의 기본 severity가 `"warning"`인지 `app/core/results.py`에서 확인한다. 아니면 `severity="warning"`을 명시한다.)

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory backend pytest tests/test_ir_pitch.py -v` → PASS, 그다음 `uv run --directory backend pytest` → 전체 PASS (아직 등록 전이라 기존 테스트는 그대로).

- [ ] **Step 5: Commit**

```bash
git add backend/app/harness/tasks/ir_pitch backend/tests/test_ir_pitch.py
git commit -m "IR 피치덱 결과 스키마와 검증 규칙"
```

---

### Task 2: IR 정책·생성 지침·시나리오와 과제 등록

**Files:**
- Create: `backend/app/harness/tasks/ir_pitch/harness.py`
- Create: `backend/app/harness/tasks/ir_pitch/policy.yaml`
- Create: `backend/app/harness/tasks/ir_pitch/prompts/generate.md`
- Create: `backend/app/harness/tasks/ir_pitch/evals/basic.yaml`
- Create: `backend/app/harness/tasks/ir_pitch/evals/quick-skip.yaml`
- Modify: `backend/app/harness/registry.py:12`
- Modify: `scripts/measure_parallel.yaml` (끝에 추가)
- Modify: `backend/tests/test_api.py:31-36`, `backend/tests/test_evidence.py:120`, `backend/tests/test_images.py:113-116`, `backend/tests/test_tasks.py:226-231`
- Test: `backend/tests/test_ir_pitch.py` (테스트 추가)

**Interfaces:**
- Consumes: Task 1의 `IrPitchContent`, `VALIDATORS`; `app.harness.base.BaseHarness`; `tests.conftest.api_client`, `app.main.create_app`, `app.providers.mock.MockProvider`, `app.harness.registry.HarnessRegistry`
- Produces: `TASK_TYPES == ("business_plan", "product_planning", "branding", "marketing_content", "ir_pitch")`; API `GET /api/v1/coaching/tasks`에 `ir_pitch`가 마지막으로 나온다.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_ir_pitch.py` 끝에 더한다(import는 파일 위쪽으로 올린다):

```python
from app.harness.registry import TASK_TYPES, HarnessRegistry
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


@pytest.fixture(scope="module")
def harness():
    return HarnessRegistry(MockProvider()).get("ir_pitch")


def test_ir_pitch_is_registered_last():
    assert TASK_TYPES[-1] == "ir_pitch"


def test_policy_keeps_money_private_and_images_off(harness):
    policy = harness.policy
    assert policy.title == "IR 피치덱"
    assert policy.raw_input_field == "company_idea"
    assert policy.private_fields == ["funding_amount", "current_revenue"]
    assert policy.image_generation is False


def test_carry_over_takes_ideas_and_customers_from_earlier_tasks(harness):
    carry = harness.policy.carry_over
    assert carry["business_idea"] == "company_idea"
    assert carry["product_idea"] == "company_idea"
    assert carry["customer_problem"] == "problem"
    assert carry["target_customer"] == "target_market"
    assert carry["revenue_model"] == "business_model"


def test_mock_session_generates_a_valid_pitch_deck(harness):
    state = harness.start("한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요")
    harness.generate(state)
    content = harness.content_model.model_validate(state.result.content)
    assert 5 <= len(content.slides) <= 12
    assert state.result.sections


def test_api_runs_ir_pitch_from_business_plan_carry():
    client = api_client(create_app(provider=MockProvider()))
    prev = client.post(
        f"{BASE}/tasks/business_plan/sessions", json={"notice_acknowledged": True, "raw_input": "한글 디자인 북백 사업"}
    ).json()["session_id"]
    client.post(f"{BASE}/sessions/{prev}/generate")
    view = client.post(
        f"{BASE}/tasks/ir_pitch/sessions",
        json={"notice_acknowledged": True, "raw_input": "투자 발표 준비", "from_session_id": prev},
    ).json()
    assert view["task_type"] == "ir_pitch"
    company = next(s for s in view["summary"] if s["field"] == "company_idea")
    assert (company["value"], company["source"]) == ("한글 디자인 북백 사업", "previous_task")
```

`harness.start(raw_input, mode=..., context=...)`, `harness.generate(state) -> None`(`backend/app/harness/base.py`), 세션 응답의 기준 목록 `view["summary"]`(항목 `field`·`value`·`source`)은 `backend/tests/test_api_carry.py`와 같은 방식이다. 사업계획의 처음 입력 필드는 `business_idea`이고 IR `carry_over`가 그것을 `company_idea`로 받는다.

기존 테스트의 기대값을 고친다:
- `backend/tests/test_api.py` `test_list_tasks`: 목록 끝에 `"ir_pitch"`.
- `backend/tests/test_evidence.py` `test_evidence_api`: 사전에 `"ir_pitch": 0`.
- `backend/tests/test_images.py` `test_branding_and_marketing_turn_images_on_by_default`: 사전에 `"ir_pitch": False`.
- `backend/tests/test_tasks.py` `test_private_fields_starting_values` 매개변수에 `("ir_pitch", ["funding_amount", "current_revenue"])`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory backend pytest tests/test_ir_pitch.py tests/test_api.py tests/test_evidence.py tests/test_images.py tests/test_tasks.py -q`
Expected: FAIL (`ir_pitch` 미등록, `UnknownTaskError`/목록 불일치)

- [ ] **Step 3: Write the implementation**

`backend/app/harness/tasks/ir_pitch/harness.py`:

```python
"""IR 피치덱 하네스. 바꾸고 싶은 단계만 BaseHarness 메서드를 오버라이드한다."""
from app.harness.base import BaseHarness

from .output_schema import IrPitchContent
from .validators import VALIDATORS


class Harness(BaseHarness):
    content_model = IrPitchContent
    validators = VALIDATORS
```

`backend/app/harness/tasks/ir_pitch/policy.yaml`:

```yaml
task_type: ir_pitch
title: IR 피치덱
description: 투자자를 설득할 발표 흐름과 슬라이드별 원고를 정리해요.
heading: 투자자 앞에서 발표할 자료가 필요해요
deliverable: 피치덱 슬라이드 · 발표 원고
input_placeholder: 예) 한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요
input_examples:
  - 한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요
  - 반려견 산책 대행 앱으로 정부 지원사업에 지원하려고 해요
raw_input_field: company_idea
readiness_threshold: 0.7
question_caps: { quick: 3, standard: 5, precise: 10 }
max_easier_level: 4
fields:
  - name: company_idea
    label: 사업 한 줄 소개
    kind: must_confirm
    weight: 3
    question: 투자자에게 이 사업을 한 문장으로 소개한다면 어떻게 말할까요?
    easier_questions:
      - question: 무엇을, 누구에게 파는 사업인지 짧게 말해 주세요.
  - name: problem
    label: 해결할 문제
    kind: must_confirm
    weight: 3
    question: 고객이 겪는 문제 중 이 사업이 해결하는 것은 무엇인가요?
    easier_questions:
      - question: 이 사업이 없으면 고객은 어떤 점이 가장 불편할까요?
      - question: 아래 중 가장 가까운 불편을 골라 주세요.
        options: [시간이 오래 걸린다, 비용이 비싸다, 마음에 드는 선택지가 없다, 방법을 잘 모른다]
  - name: solution
    label: 해결 방식
    kind: must_confirm
    weight: 3
    question: 그 문제를 어떤 방식으로 해결하나요?
    easier_questions:
      - question: 다른 곳과 비교해 이 사업만 다르게 하는 점 하나를 말해 주세요.
  - name: target_market
    label: 목표 시장·고객
    kind: must_confirm
    weight: 2
    question: 가장 먼저 공략할 시장과 고객은 누구인가요?
    options: [20~30대 직장인, 자녀를 둔 부모, 대학생, 소상공인]
    easier_questions:
      - question: 둘 중 더 가까운 쪽을 골라 주세요.
        options: [개인 고객, 가게·회사 같은 사업자]
  - name: business_model
    label: 수익 구조
    kind: ai_suggest
    weight: 2
    question: 어떻게 돈을 버나요?
    options: [제품 판매, 구독, 수수료, 광고]
    easier_questions:
      - question: 고객이 돈을 내는 순간은 언제인가요?
  - name: traction
    label: 지금까지의 성과
    kind: ai_suggest
    weight: 2
    question: 지금까지 확인한 성과가 있나요?
    options: [아직 없음, 시제품 완성, 첫 판매 발생, 사전 신청자 확보, 고객 인터뷰 진행]
    multi_select: true
    easier_questions:
      - question: 고객 반응을 직접 확인해 본 적이 있나요? 있다면 어떤 반응이었나요?
  - name: competition
    label: 경쟁과 차별점
    kind: ai_suggest
    weight: 1
    question: 비슷한 제품이나 서비스와 비교해 무엇이 다른가요?
    options: [더 저렴하다, 디자인이 다르다, 더 빠르다, 직접 만든다]
    easier_questions:
      - question: 고객이 이 사업 대신 고를 만한 다른 선택지는 무엇인가요?
  - name: team
    label: 팀
    kind: ai_suggest
    weight: 1
    question: 이 사업을 하는 팀은 누구이고 어떤 강점이 있나요?
    options: [혼자 운영, 디자이너 포함, 개발자 포함, 업계 경력 보유]
    multi_select: true
    easier_questions:
      - question: 이 사업을 잘 해낼 수 있는 이유를 하나만 말해 주세요.
  - name: investment_purpose
    label: 투자 유치 목적
    kind: ai_suggest
    weight: 2
    question: 투자를 받으면 어디에 쓰고 싶나요?
    options: [제품 개발, 마케팅, 제작 설비, 인력 채용]
    multi_select: true
    easier_questions:
      - question: 돈이 생긴다면 가장 먼저 해결하고 싶은 일은 무엇인가요?
private_fields: [funding_amount, current_revenue]
supplement_fields:
  - { name: funding_amount, label: 희망 투자 금액, example: 시드 3억 원 }
  - { name: current_revenue, label: 현재 매출, example: 월 200만 원 }
  - { name: investor_type, label: 투자자 유형, example: 액셀러레이터 }
  - { name: pitch_length, label: 발표 시간, example: 5분 }
carry_over: { business_idea: company_idea, product_idea: company_idea, product_and_customer: company_idea, product: company_idea, customer_problem: problem, target_customer: target_market, user: target_market, core_customer: target_market, revenue_model: business_model, differentiation: competition }
rules:
  - 근거 없는 시장 규모·기업가치를 사실처럼 제시하지 않는다
  - 임의의 매출 전망이나 성장률을 만들지 않는다
  - 확인하지 않은 성과·투자 유치 이력을 사실처럼 쓰지 않는다
  - 투자 수익을 보장하는 표현을 쓰지 않는다
```

`backend/app/harness/tasks/ir_pitch/prompts/generate.md`:

```
{% extends "_generate_base.md" %}
{% block task_guidance %}

## IR 피치덱 지침
- 문제 → 해결 → 시장 → 비즈니스 모델 → 성과 → 경쟁 → 팀 → 재무 계획 → 투자 요청 순서로 투자자를 설득하는 하나의 이야기로 쓴다.
- 슬라이드마다 headline은 그 장의 주장 한 문장, script는 발표자가 소리 내어 읽을 원고로 쓴다.
- 정보가 없는 슬라이드(성과·팀 등)는 지어내지 말고 "확인할 것"으로 적거나 빼되, 문제·해결·투자 요청 슬라이드는 반드시 넣는다.
- 성과가 아직 없다면 검증 계획을 성과 대신 보여 준다.
- investor_questions에는 투자자가 실제로 물을 만한 날카로운 질문을 적는다.
- 카드는 진단 1~2개(설득력이 약한 지점), 제안 2~3개(슬라이드 흐름과 핵심 메시지), 실행 과제 2~3개(발표 전 준비할 것)로 구성한다.
{% endblock %}
```

(다른 과제의 `prompts/generate.md`와 같은 구조다. 빈 줄이 두 개 연속 나오지 않게 한다.)

`backend/app/harness/tasks/ir_pitch/evals/basic.yaml`:

```yaml
name: 한글 굿즈 시드 투자 기본 흐름
raw_input: 한글 디자인 굿즈 브랜드로 시드 투자를 받고 싶어요
answers:
  problem:
    - answer_type: easier
    - value: 외국인 관광객이 살 만한 세련된 한글 기념품이 적다
  solution:
    - value: 한글 자모를 패턴으로 쓴 생활용품을 직접 디자인해 판다
  target_market:
    - answer_type: option
      option_indexes: [0]
```

`backend/app/harness/tasks/ir_pitch/evals/quick-skip.yaml`:

```yaml
# 빠른 모드에서 질문마다 '아직 모르겠어요'. 정보가 적을 때 가정·미정 처리를 본다(실제 모델 측정용, Mock 회귀도 통과).
name: 모두 모름 빠른 IR 피치덱
raw_input: 동네 반찬 구독 서비스로 투자를 받고 싶어요
mode: quick
```

(시나리오 키·흐름은 `business_plan/evals/*.yaml`과 같다. `basic.yaml`의 답 순서는 정책의 질문 순서(필드 순서)를 따르므로, 실제 Mock 흐름에서 쓰이지 않는 답이 남아 실패하면 `uv run --directory backend pytest tests/test_tasks.py -k ir_pitch -q`의 메시지를 보고 답을 실제 묻는 필드에 맞춘다.)

`backend/app/harness/registry.py`:

```python
TASK_TYPES = ("business_plan", "product_planning", "branding", "marketing_content", "ir_pitch")
```

`scripts/measure_parallel.yaml` 끝에 더한다:

```yaml
ir_pitch:
  max_workers: 2
  parts:
    - name: story
      content: [one_liner, slides]
    - name: ask
      content: [ask, investor_questions]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --directory backend pytest` → 전체 PASS (`test_tasks.py`의 과제별 정책·템플릿·시나리오 검사와 `test_measure.py`의 조각 검사가 `ir_pitch`까지 돈다)

- [ ] **Step 5: Commit**

```bash
git add backend/app/harness/tasks/ir_pitch backend/app/harness/registry.py scripts/measure_parallel.yaml backend/tests
git commit -m "IR 피치덱 과제 등록: 정책·생성 지침·시나리오"
```

---

### Task 3: 프론트 — 홈 카드 다섯 개와 미리보기

**Files:**
- Modify: `frontend/src/preview/fixtures.ts:5-37` (`TASKS`)
- Modify: `frontend/src/screens/HomeScreen.tsx:12` (주석)
- Modify: `frontend/src/styles/screens.css:7` 근처
- Test: `frontend/src/app/view.test.tsx` ("홈은 과제 카드" 근처에 테스트 추가)

**Interfaces:**
- Consumes: `TaskSummary`(`frontend/src/api/types`), `HomeScreen` props `{ tasks, sessions, onStart, onResume, onWork }`
- Produces: 미리보기 `TASKS`가 5개(마지막 `ir_pitch`).

- [ ] **Step 1: Write the failing test**

프론트 화면 테스트는 `renderToString`으로 그린 HTML 문자열을 검사한다(클릭 테스트 없음). `frontend/src/app/view.test.tsx`의 `draw` 도우미를 그대로 쓴다. 파일 위쪽 import에 `import { TASKS } from "../preview/fixtures";`를 더하고 `describe("renderScreen", ...)` 안에 넣는다:

```tsx
  it("홈은 API가 준 과제를 모두 카드로(IR 피치덱 포함)", () => {
    expect(TASKS.map((t) => t.task_type)).toEqual([
      "business_plan",
      "product_planning",
      "branding",
      "marketing_content",
      "ir_pitch",
    ]);
    const { main } = draw({ kind: "home", tasks: TASKS, sessions: [] });
    expect(main.match(/class="card task stack"/g)).toHaveLength(5);
    expect(main).toContain("IR 피치덱 시작하기 →");
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- view`
Expected: FAIL (TASKS가 4개)

- [ ] **Step 3: Write minimal implementation**

`frontend/src/preview/fixtures.ts`의 `TASKS` 끝에 더한다(`PRODUCT = TASKS[1]` 등 인덱스 참조는 그대로 유지):

```ts
  {
    task_type: "ir_pitch",
    title: "IR 피치덱",
    description: "투자자를 설득할 발표 흐름과 슬라이드별 원고를 정리해요.",
    heading: "투자자 앞에서 발표할 자료가 필요해요",
    deliverable: "피치덱 슬라이드 · 발표 원고",
    evidence_sources: 0,
  },
```

`frontend/src/screens/HomeScreen.tsx` 주석: `/** 홈: 과제 중 하나를 고른다. ... */` ("네 개" 삭제 — 과제 수는 API가 정한다).

`frontend/src/styles/screens.css` `.taskgrid` 다음 줄에 더한다(두 칸 배치에서 홀수 개면 마지막 카드가 줄 전체를 쓴다. 모바일 한 칸 배치에는 영향 없음):

```css
.taskgrid > .task:last-child:nth-child(odd) { grid-column: 1 / -1; }
```

- [ ] **Step 4: Run tests and build**

Run: `npm --prefix frontend test` → 전체 PASS, `npm --prefix frontend run build` → OK (`tokens.test.ts`가 CSS 값 규칙을 검사한다 — 새 줄에는 색·크기 값이 없다)

- [ ] **Step 5: Commit**

```bash
git add frontend/src
git commit -m "홈과 미리보기에 IR 피치덱 과제 카드"
```

---

### 마무리 (컨트롤러)

- 브라우저 확인: 백엔드·프론트를 띄워 홈에 카드 5개, IR 과제로 질문 → 생성 → 결과 문서 내려받기(PDF)까지 Mock으로 한 번.
- 문서: `README.md`(과제 5개), `docs/DEMO.md:23`, `docs/DEPLOY.md:36,54,99`("과제 4개" → "과제 5개"), `docs/HANDOFF.md`(기준일·main·테스트 수·지금 상태 표·다음 할 일).
- WBS: `uv run --no-project --with openpyxl python scripts/wbs.py add ...`로 "IR 피치덱 과제 추가" 행(완료·PR #36), `date`로 기준일.
- PR `task/36-ir-task` → 사용자가 머지.
