# 외부 AI로 나가는 내용 보호 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 외부 AI로 나가는 프롬프트에서 개인정보를 자동으로 가리고, 비공개 항목(정책 기본값 + 사용자 설정)의 값을 빼며, 세션을 만들 때 외부 전송 고지에 동의받는다. trace에도 가린 내용만 남는다.

**Architecture:** 설계서 `docs/superpowers/specs/2026-10-18-outbound-privacy-design.md`를 따른다. 판단은 새 모듈 `backend/app/harness/privacy.py`의 순수 함수(`redact`, `private_names`, `masked_state`, `outbound_prompt`)이고, 외부로 나가는 두 길목(`BaseHarness._call`, `BaseHarness.illustrate`)이 같은 함수를 쓴다. 비공개 설정은 답변·답 고치기·보완 정보 저장 요청에 함께 실려 같은 원자적 블록에서 `SessionState.private_overrides`를 고친다. 프론트는 `lib/privacy.ts`가 판단하고 입력 부품이 체크 상태를 가진다.

**Tech Stack:** FastAPI·Pydantic v2·Jinja2(백엔드), React 19·TypeScript·vitest(프론트).

## Global Constraints

- 설계서가 기준이다: `docs/superpowers/specs/2026-10-18-outbound-privacy-design.md`.
- 비공개 표시 글은 정확히 `[비공개 입력 · AI에 보내지 않음]`. 가림 표시는 `[주민번호]`·`[카드번호]`·`[계좌번호]`·`[전화번호]`·`[이메일]`.
- 고지 문구(정확히): `입력 내용은 결과를 만들기 위해 외부 AI 서비스로 전송될 수 있어요. 개인정보(주민번호·연락처·계좌 등)는 자동으로 가려서 보내고, 'AI에 보내지 않음'으로 표시한 항목은 보내지 않아요. 공개 전 아이디어·영업비밀은 표시해 주세요.` 체크 칸 라벨 `확인했어요`. 고지 버전 상수 `NOTICE_VERSION = "2026-10-18"`.
- 고지 미확인 422 문구 `외부 전송 안내를 확인해 주세요.`, 모르는 비공개 이름 422 문구 `비공개로 정할 수 없는 항목입니다: {이름들}`(모두 `app/core/messages.py`).
- 체크 칸 라벨 `🔒 이 답은 AI에 보내지 않기`(질문·답 고치기), `AI에 보내지 않기`(보완 항목), 기준 표 표시 `AI에 보내지 않음`.
- 세션 상태(사실·보완 정보·요청 글)에는 원래 값이 남는다. 걸러지는 것은 프롬프트와 trace뿐이다. 서버 화면·결과 문서·내려받기에는 사용자 값이 그대로 보인다.
- 판단은 순수 함수(`[코드·순수]` docstring), 상태 변경은 하네스 메서드 한 곳. 응답 모델은 `ContractModel`. 프론트는 reducer만 상태를 바꾸고 컴포넌트는 props만(입력 중 체크 상태는 그 부품 안). CSS는 토큰과 `@container`, 미리보기 프레임에 스크롤 상자 없음, jsdom·새 패키지 없음.
- 커밋·PR에 AI 공동저자·생성 표기 금지. `backend/.env` 금지. 실제 API 호출 금지(Mock).
- PR 직전 WBS(`scripts/wbs.py add`로 새 행)와 `docs/HANDOFF.md`·`README.md`를 같은 PR에서 고친다.
- 명령: `uv run --directory backend pytest -q`, `npm --prefix frontend test`, `npm --prefix frontend run gen:api`, `npm --prefix frontend run build`.

---

### Task 1: 프롬프트 거르기(개인정보 가림·비공개 값 빼기)와 두 길목 적용

**Files:**
- Create: `backend/app/harness/privacy.py`, `backend/tests/test_privacy.py`
- Modify: `backend/app/harness/policy.py`(`private_fields`), `backend/app/core/state.py`(`private_overrides`), `backend/app/harness/base.py`(`_call`, `illustrate`), 과제 정책 3개(`private_fields` 시작값)
- Test: `backend/tests/test_tasks.py`(정책 검증), `backend/tests/test_privacy.py`

**Interfaces:**
- Produces:
  - `privacy.PRIVATE_MARK = "[비공개 입력 · AI에 보내지 않음]"`
  - `privacy.redact(text: str) -> tuple[str, dict[str, int]]`
  - `privacy.private_names(defaults: Iterable[str], overrides: Mapping[str, bool]) -> frozenset[str]`
  - `privacy.masked_state(state: SessionState, private: frozenset[str]) -> SessionState`
  - `privacy.outbound_prompt(prompt: Prompt) -> tuple[Prompt, dict[str, int]]`
  - `TaskPolicy.private_fields: list[str] = []`(필드·보완 항목 이름만, 아니면 읽을 때 오류)
  - `SessionState.private_overrides: dict[str, bool] = {}`
  - `BaseHarness.private(state) -> frozenset[str]`(= `private_names(self.policy.private_fields, state.private_overrides)`)
  - trace 항목 `input`에 `redactions: dict[str, int]`(가린 것이 없으면 `{}`)

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_privacy.py`:

```python
"""외부로 나가는 프롬프트 거르기: 개인정보 가림(되돌리지 않음), 비공개 값 빼기. 세션 상태는 그대로다."""
import pytest

from app.core.state import CarriedContext, CarriedItem, InfoItem, InfoSource
from app.harness.privacy import PRIVATE_MARK, masked_state, outbound_prompt, private_names, redact
from app.providers.base import Prompt


@pytest.mark.parametrize(
    ("text", "masked", "kind"),
    [
        ("주민번호 900101-1234567 입니다", "주민번호 [주민번호] 입니다", "resident"),
        ("9001011234567", "[주민번호]", "resident"),
        ("카드 1234-5678-9012-3456", "카드 [카드번호]", "card"),
        ("카드 1234 5678 9012 3456", "카드 [카드번호]", "card"),
        ("계좌 110-123-456789로", "계좌 [계좌번호]로", "account"),
        ("연락처 010-1234-5678", "연락처 [전화번호]", "phone"),
        ("연락처 01012345678", "연락처 [전화번호]", "phone"),
        ("가게 02-345-6789", "가게 [전화번호]", "phone"),
        ("메일 a.b+c@ex-ample.co.kr 로", "메일 [이메일] 로", "email"),
    ],
)
def test_redact_masks_each_kind(text, masked, kind):
    assert redact(text) == (masked, {kind: 1})


@pytest.mark.parametrize("text", ["판매가 18,000원", "2026년 10월 18일", "500개 생산", "원가 8000원 / 개", "버전 1.2.3"])
def test_redact_leaves_prices_dates_and_quantities(text):
    assert redact(text) == (text, {})


def test_redact_counts_repeats():
    assert redact("010-1111-2222, 010-3333-4444")[1] == {"phone": 2}


def test_private_names_overrides_win_and_false_removes():
    assert private_names(["a", "b"], {}) == frozenset({"a", "b"})
    assert private_names(["a", "b"], {"b": False, "c": True}) == frozenset({"a", "c"})


def test_masked_state_hides_private_values_but_keeps_the_original(harness):
    state = harness.start("향초")
    field = harness.policy.fields[1].name
    state.facts[field] = InfoItem(value="비밀 값", source=InfoSource.USER_FREE_TEXT)
    state.supplements["material"] = InfoItem(value="비밀 소재", source=InfoSource.USER_SUPPLEMENT)
    state.context = CarriedContext(
        session_id="s", task_type="t", version=1, title="t", summary="s",
        items=[CarriedItem(field=field, value="비밀 값", from_name=field)],
    )

    masked = masked_state(state, frozenset({field, "material"}))

    assert masked.facts[field].value == PRIVATE_MARK
    assert masked.supplements["material"].value == PRIVATE_MARK
    assert masked.context.items[0].value == PRIVATE_MARK
    assert state.facts[field].value == "비밀 값"  # 원본은 그대로


def test_outbound_prompt_redacts_both_parts_and_sums_counts():
    prompt, counts = outbound_prompt(Prompt(system="고정 010-1234-5678", user="메일 a@b.co 와 010-9999-8888"))
    assert prompt == Prompt(system="고정 [전화번호]", user="메일 [이메일] 와 [전화번호]")
    assert counts == {"phone": 2, "email": 1}


def test_every_llm_call_sends_and_traces_only_filtered_prompts(harness):
    harness.policy.private_fields = ["material"]
    state = harness.start("향초 연락처 010-1234-5678")
    harness.set_supplements(state, {"material": "아주 비밀스러운 소재"})
    harness.generate(state)

    for entry in state.trace:
        text = f"{entry.input.get('system', '')}\n{entry.input.get('user', '')}"
        if entry.input:
            assert "010-1234-5678" not in text
            assert "아주 비밀스러운 소재" not in text
    generate = next(t for t in state.trace if t.stage == "generate" and t.input)
    assert "[전화번호]" in generate.input["user"] and PRIVATE_MARK in generate.input["user"]
    assert generate.input["redactions"] == {"phone": 1}
    assert state.raw_input == "향초 연락처 010-1234-5678"  # 세션 값은 그대로
```

그리고 이미지 단계도 같은 거르기를 거치는지 확인한다(`tests/test_images.py` 패턴으로 `image_generation` 켠 하네스, 요청 글에 전화번호 → `image` trace의 user에 없음).

`tests/test_tasks.py`에: 정책 `private_fields`에 필드·보완 항목이 아닌 이름이 있으면 `TaskPolicy.model_validate`가 `private_fields` 오류를 낸다. 과제 4개 정책의 `private_fields`가 설계서 시작값과 같다(상품기획 `production_cost`·`sale_price`, 사업계획 `revenue_model`·`production_cost`·`sale_price`·`budget`, 마케팅 `price`, 브랜딩 없음).

- [ ] **Step 2: 실패 확인** — `uv run --directory backend pytest tests/test_privacy.py -q` → FAIL

- [ ] **Step 3: 구현** — `backend/app/harness/privacy.py`:

```python
"""외부 AI로 나가는 내용 거르기. 모두 순수 함수다.

세션 상태에는 원래 값이 남고, 프롬프트와 trace에만 거른 내용이 들어간다(설계서 2026-10-18-outbound-privacy-design).
"""
import re
from collections.abc import Iterable, Mapping

from app.core.state import SessionState
from app.providers.base import Prompt

PRIVATE_MARK = "[비공개 입력 · AI에 보내지 않음]"

# 겹치면 앞 줄이 먼저 바꾼다(주민번호·카드번호가 전화번호·계좌번호로 잘못 잡히지 않게)
_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("resident", "[주민번호]", re.compile(r"(?<!\d)\d{6}-?[1-8]\d{6}(?!\d)")),
    ("card", "[카드번호]", re.compile(r"(?<!\d)\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}(?!\d)")),
    ("phone", "[전화번호]", re.compile(r"(?<!\d)(?:01[016789]|0\d{1,2})[-. ]?\d{3,4}[-. ]?\d{4}(?!\d)")),
    ("account", "[계좌번호]", re.compile(r"(?<!\d)\d{2,6}-\d{2,6}-\d{2,6}(?:-\d{1,6})?(?!\d)")),
    ("email", "[이메일]", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """[순수] 개인정보 패턴을 표시 글로 바꾸고 종류별 개수를 돌려준다. 되돌리지 않는다."""
    counts: dict[str, int] = {}
    for kind, mark, pattern in _PATTERNS:
        text, n = pattern.subn(mark, text)
        if n:
            counts[kind] = counts.get(kind, 0) + n
    return text, counts
```

(전화번호 패턴이 계좌번호 `110-123-456789`를 먹지 않는지, `02-345-6789`가 전화번호인지 테스트로 확인하고 패턴 순서·모양을 맞춘다. 테스트가 기준이다.)

```python
def private_names(defaults: Iterable[str], overrides: Mapping[str, bool]) -> frozenset[str]:
    """[순수] 비공개 이름: 정책 기본값에 사용자 설정(True 더함, False 뺌)을 덮은 것."""
    names = set(defaults)
    for name, private in overrides.items():
        (names.add if private else names.discard)(name)
    return frozenset(names)


def _mask(items, private):
    return {name: (item.model_copy(update={"value": PRIVATE_MARK}) if name in private else item) for name, item in items.items()}


def masked_state(state: SessionState, private: frozenset[str]) -> SessionState:
    """[순수] 비공개 이름의 사실·가정·보완 정보·가져온 값을 표시 글로 바꾼 복사본(프롬프트 렌더용)."""
    update = {
        "facts": _mask(state.facts, private),
        "assumptions": _mask(state.assumptions, private),
        "supplements": _mask(state.supplements, private),
    }
    if state.context is not None:
        items = [i.model_copy(update={"value": PRIVATE_MARK}) if i.field in private else i for i in state.context.items]
        update["context"] = state.context.model_copy(update={"items": items})
    return state.model_copy(update=update)


def outbound_prompt(prompt: Prompt) -> tuple[Prompt, dict[str, int]]:
    """[순수] system·user 둘 다 개인정보를 가린다. 개수는 합친다."""
    system, a = redact(prompt.system)
    user, b = redact(prompt.user)
    return Prompt(system=system, user=user), {k: a.get(k, 0) + b.get(k, 0) for k in a.keys() | b.keys()}
```

`backend/app/harness/policy.py`의 `TaskPolicy`에 `private_fields: list[str] = Field(default_factory=list)  # AI에 보내지 않는 기본 항목(필드·보완 항목 이름)`, `_check_fields` 끝에 모르는 이름이면 `ValueError(f"private_fields에 모르는 이름이 있습니다: …")`.

`backend/app/core/state.py`의 `SessionState`에 `private_overrides: dict[str, bool] = Field(default_factory=dict)  # 사용자가 바꾼 비공개 설정(정책 기본값보다 우선)`.

`backend/app/harness/base.py`:
- `from app.harness.privacy import masked_state, outbound_prompt, private_names`
- 메서드 `def private(self, state: SessionState) -> frozenset[str]: return private_names(self.policy.private_fields, state.private_overrides)`
- `_call`: `prompt = self.prompts.render(stage, state=masked_state(state, self.private(state)), policy=…, profile=…, **context)` 다음 `prompt, redactions = outbound_prompt(prompt)`. 두 trace 항목의 `input`에 `"redactions": redactions`.
- `illustrate`: 같은 방식(`state=masked_state(...)`, `outbound_prompt`, trace `input`에 `redactions`). 섹션 글(`text=section_text(target)`)도 `outbound_prompt`가 user 블록에서 가린다.

과제 정책에 시작값: `product_planning/policy.yaml` `private_fields: [production_cost, sale_price]`, `business_plan/policy.yaml` `private_fields: [revenue_model, production_cost, sale_price, budget]`, `marketing_content/policy.yaml` `private_fields: [price]`.

- [ ] **Step 4: 통과 확인** — `uv run --directory backend pytest -q` → PASS(시나리오·템플릿 테스트 포함)

- [ ] **Step 5: 커밋**

```bash
git add backend
git commit -m "외부로 나가는 프롬프트 거르기: 개인정보 자동 가림·비공개 항목 값 빼기(_call·image 공통), trace에도 거른 내용만"
```

---

### Task 2: 비공개 설정·고지 동의 API와 결과 최신 여부

**Files:**
- Modify: `backend/app/core/state.py`(`ResultVersion.private`, `notice_version`, `notice_acknowledged_at`), `backend/app/harness/base.py`(`start`, `apply_answer`, `revise_answer`, `set_supplements`, `new_version`, `privacy_changed`), `backend/app/core/messages.py`, `backend/app/schemas/coaching.py`, `backend/app/api/views.py`, `backend/app/api/coaching.py`
- Test: `backend/tests/test_privacy_api.py`(새), 기존 테스트(세션 만들기 본문에 `notice_acknowledged: true`)

**Interfaces:**
- Consumes: Task 1의 `private_names`, `BaseHarness.private`, `SessionState.private_overrides`.
- Produces:
  - `privacy.NOTICE_VERSION = "2026-10-18"`
  - `BaseHarness.start(..., notice_acknowledged_at: datetime | None = None)` → 세션 `notice_version`·`notice_acknowledged_at`
  - `apply_answer(state, answer, private: bool | None = None)`, `revise_answer(state, answer, private: bool | None = None)`, `set_supplements(state, values, private: Mapping[str, bool] | None = None)` — 같은 원자적 블록에서 `_set_private(state, name, value)`(정책 기본값과 같아지면 덮어쓴 값을 지운다). 모르는 이름은 `HarnessError(private_unknown_message(names))`
  - `privacy_changed(private: frozenset[str], latest: ResultVersion) -> bool`(순수), 최신 여부 = `answers_changed or supplements_changed or privacy_changed`(결과가 있을 때만, `set_supplements`·비공개만 바뀐 답 고치기 모두)
  - `ResultVersion.private: list[str]`(정렬, 스냅샷), `generate_reason`은 그대로(비공개만 바뀌면 `regenerate`)
  - 요청: `CreateSessionRequest.notice_acknowledged: bool`(필수), `AnswerRequest.private: bool | None = None`, `ReviseAnswerRequest.private: bool | None = None`, `SupplementsRequest.private: dict[str, bool] = {}`
  - 응답: `SummaryItem.private: bool`, `SupplementItem.private: bool`, `SessionView.private_names: list[str]`
  - `messages.NOTICE_REQUIRED_MESSAGE = "외부 전송 안내를 확인해 주세요."`, `messages.private_unknown_message(names) -> "비공개로 정할 수 없는 항목입니다: …"`

- [ ] **Step 1: 실패 테스트** — `backend/tests/test_privacy_api.py`:

```python
"""비공개 설정은 답·보완 정보 요청에 실린다. 고지 동의가 있어야 세션을 만든다."""
from app.core.messages import NOTICE_REQUIRED_MESSAGE
from app.main import create_app
from app.providers.mock import MockProvider
from tests.conftest import api_client

BASE = "/api/v1/coaching"


def new_session(client, task="product_planning", text="향초"):
    return client.post(f"{BASE}/tasks/{task}/sessions", json={"raw_input": text, "notice_acknowledged": True}).json()


def test_creating_a_session_needs_the_notice():
    client = api_client(create_app(provider=MockProvider()))
    missing = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초"})
    refused = client.post(f"{BASE}/tasks/product_planning/sessions", json={"raw_input": "향초", "notice_acknowledged": False})
    assert missing.status_code == 422
    assert (refused.status_code, refused.json()["detail"]) == (422, NOTICE_REQUIRED_MESSAGE)
    view = new_session(client)
    assert view["private_names"] == ["production_cost", "sale_price"]
    assert {s["name"]: s["private"] for s in view["supplements"]}["sale_price"] is True


def test_answer_can_mark_its_field_private():
    client = api_client(create_app(provider=MockProvider()))
    view = new_session(client)
    q = view["next_question"]
    after = client.post(
        f"{BASE}/sessions/{view['session_id']}/answers",
        json={"question_id": q["question_id"], "answer_type": "free_text", "value": "비밀 답", "private": True},
    ).json()
    assert q["field"] in after["private_names"]
    assert next(s for s in after["summary"] if s["field"] == q["field"])["private"] is True


def test_supplements_can_unmark_a_default_private_item_and_reject_unknown_names():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    saved = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"sale_price": "18,000원"}, "private": {"sale_price": False}}).json()
    assert "sale_price" not in saved["private_names"]
    bad = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"nope": True}})
    assert bad.status_code == 422


def test_changing_only_privacy_makes_the_result_stale_and_reverting_makes_it_current():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    client.post(f"{BASE}/sessions/{sid}/generate")
    stale = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"sale_price": False}}).json()
    assert stale["result_stale"] is True
    back = client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {}, "private": {"sale_price": True}}).json()
    assert back["result_stale"] is False


def test_result_view_marks_private_rows_from_its_version():
    client = api_client(create_app(provider=MockProvider()))
    sid = new_session(client)["session_id"]
    client.put(f"{BASE}/sessions/{sid}/supplements", json={"values": {"sale_price": "18,000원"}})
    result = client.post(f"{BASE}/sessions/{sid}/generate").json()
    assert next(s for s in result["supplements"] if s["name"] == "sale_price")["private"] is True
```

하네스 단위 테스트도 더한다(`tests/test_privacy.py`에): `start`가 `notice_version == NOTICE_VERSION`과 넘긴 동의 시각을 남긴다; `_set_private`가 정책 기본값과 같아지면 `private_overrides`에서 지운다; 비공개만 바꾼 `revise_answer`(같은 값 + `private=True`)가 결과를 최신 아님으로 만든다; 모르는 이름 `HarnessError`; 실패한 답(예: 없는 선택지)이면 비공개 설정도 되돌아간다(원자성).

기존 테스트·`scripts/claude_smoke.py`·시나리오 실행기(`app/harness/evals.py`)에서 세션을 만드는 곳은 동의 시각을 넘기거나(`start(..., notice_acknowledged_at=...)` 선택 인자라 하네스 직접 호출은 그대로 둬도 된다) API 본문에 `"notice_acknowledged": True`를 넣는다.

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**
  - `state.py`: `SessionState.notice_version: str = ""`, `notice_acknowledged_at: datetime | None = None`; `ResultVersion.private: list[str] = Field(default_factory=list)`, `snapshot`·`derived`에 `private` 인자를 더해 복사(파생 버전은 직전 버전 것을 이어받는다).
  - `base.py`: `privacy_changed(private, latest) -> bool: return sorted(private) != latest.private`(순수). `new_version`은 `sorted(self.private(state))` 대신 상태만 받는 순수 함수이므로 인자로 `private: frozenset[str]`를 더해 넘긴다(`generate`에서 `self.private(state)`). 최신 여부를 다시 정하는 곳(`set_supplements`, 그리고 새로 비공개만 바뀌는 `apply_answer`/`revise_answer` 경로)은 공용 도우미 `_restale(state)`(결과가 있으면 `answers_changed or supplements_changed or privacy_changed`)로 모은다. `set_supplements`의 기존 "값이 같으면 아무것도 안 함"은 "값도 비공개도 같으면"으로 바꾼다.
  - `_set_private(state, name, value)`: 정책 기본값(`name in self.policy.private_fields`)과 같으면 `state.private_overrides.pop(name, None)`, 다르면 저장. 이름 확인은 `self.policy.labels | self.policy.supplement_labels`.
  - `start`: `notice_version=NOTICE_VERSION`, `notice_acknowledged_at=notice_acknowledged_at`.
  - `schemas/coaching.py`: 위 요청·응답 필드. `CreateSessionRequest.notice_acknowledged: bool`(필수).
  - `api/coaching.py`: `create_session`에서 `if not body.notice_acknowledged: raise HTTPException(422, NOTICE_REQUIRED_MESSAGE)`(라우터는 얇게: 판정은 이 한 줄), `harness.start(..., notice_acknowledged_at=utcnow())`. 답·답 고치기는 `Answer(**body.model_dump(exclude={"private"}))`와 `private=body.private`, 보완 정보는 `private=body.private`.
  - `api/views.py`: `build_summary(fields, facts, assumptions, private)`·`supplement_items(fields, values, private)`에 비공개 집합을 넘겨 `private` 칸을 채운다. 세션 뷰는 `harness.private(state)`, 결과·버전 뷰는 `frozenset(version.private)`. `SessionView.private_names=sorted(harness.private(state))`.

- [ ] **Step 4: 통과 확인** — `uv run --directory backend pytest -q` → PASS(`test_contract.py` 포함)

- [ ] **Step 5: 커밋**

```bash
git add backend scripts
git commit -m "비공개 설정·고지 동의 API: 답·보완 정보 요청에 private, 세션 만들 때 동의, 비공개만 바뀌어도 결과 최신 아님"
```

---

### Task 3: 프론트 판단·요청(비공개·고지)

**Files:**
- Regenerate: `frontend/src/api/schema.d.ts`; Modify: `frontend/src/api/coaching.ts`, `frontend/src/api/types.ts`
- Create: `frontend/src/lib/privacy.ts`, `frontend/src/lib/privacy.test.ts`
- Modify: `frontend/src/app/state.ts`(과제별 고지 확인), `frontend/src/app/handlers.ts`, `frontend/src/app/view.tsx`(Handlers 타입), `frontend/src/preview/handlers.ts`, `frontend/src/testing/factories.ts`, `frontend/src/preview/fixtures.ts`
- Test: 옆의 `*.test.ts`

**Interfaces:**
- Consumes: Task 2의 API.
- Produces:
  - `lib/privacy.ts`: `NOTICE_TEXT`(Global Constraints 문구), `isPrivate(privateNames: string[], name: string): boolean`, `privateChanges(initial: Record<string, boolean>, current: Record<string, boolean>): Record<string, boolean>`(바뀐 것만)
  - `createSession(task, rawInput, mode, from, noticeAcknowledged: boolean)`; `submitAnswer(sessionId, questionId, body)`의 `body.private?`; `reviseAnswer`의 `body.private?`; `saveSupplements(sessionId, values, privacy: Record<string, boolean>)`
  - state: `notices: Record<string, boolean>`(과제별 고지 확인), 동작 `noticeChanged { task, acknowledged }`
  - Handlers: `acknowledgeNotice(task: string, acknowledged: boolean)`, `saveSupplements(values, privacy)`(시그니처 확장), `answer(body)`·`revise(questionId, body)`의 body에 `private` 포함 가능
  - `pickMode`는 `state.notices[task] === true`일 때만 세션을 만든다(아니면 아무것도 안 함)

- [ ] **Step 1: 타입 재생성** — `npm --prefix frontend run gen:api`, 빌드 오류를 팩토리·픽스처(`private: false`, `private_names: []`)로 맞춘다.
- [ ] **Step 2: 실패 테스트**
  - `lib/privacy.test.ts`: `isPrivate(["a"], "a") === true`; `privateChanges({a: true, b: false}, {a: true, b: true})` → `{b: true}`; `NOTICE_TEXT`가 정확한 문구.
  - `api/coaching.test.ts`: `createSession`이 `notice_acknowledged: true`를 싣는다; `saveSupplements(sid, values, {sale_price: false})`가 `private: {sale_price: false}`를 싣는다; `submitAnswer`가 `private`를 그대로 싣는다.
  - `app/state.test.ts`: `noticeChanged`가 그 과제의 확인 상태를 바꾼다(다른 과제는 그대로).
  - `app/handlers.test.ts`: 고지를 확인하지 않은 과제의 `pickMode`는 요청하지 않는다; 확인한 과제는 `createSession(..., true)`; `acknowledgeNotice`가 `noticeChanged`를 보낸다; `saveSupplements(values, privacy)`가 둘 다 넘긴다.
- [ ] **Step 3: 실패 확인** — FAIL
- [ ] **Step 4: 구현** — 위 Interfaces 그대로. `privateChanges`는 `Object.entries(current).filter(([k, v]) => initial[k] !== v)`로.
- [ ] **Step 5: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build` → PASS
- [ ] **Step 6: 커밋**

```bash
git add frontend
git commit -m "프론트: 고지 확인 상태·비공개 설정을 요청에 싣기(lib/privacy)"
```

---

### Task 4: 고지·비공개 체크 화면, 표시, 미리보기, 문서

**Files:**
- Modify: `frontend/src/screens/RequestScreen.tsx`, `frontend/src/screens/ModeScreen.tsx`, `frontend/src/components/QuestionCard.tsx`, `frontend/src/components/ReviseCard.tsx`, `frontend/src/components/SupplementForm.tsx`, `frontend/src/components/CriteriaBox.tsx`(또는 `lib/criteria.ts` 행에 `private`), `frontend/src/lib/documentHtml.ts`(기준 표 표시), `frontend/src/app/view.tsx`, `frontend/src/styles/screens.css`
- Modify: `frontend/src/preview/fixtures.ts`, `frontend/src/preview/frames.tsx`, `frontend/src/preview/frames.test.tsx`
- Test: `frontend/src/components/components.test.tsx`, `frontend/src/app/view.test.tsx`
- Modify: `README.md`, `docs/HANDOFF.md`, `CLAUDE.md`, `docs/WBS.xlsx`(`scripts/wbs.py add`)

**Interfaces:**
- Consumes: Task 3의 `NOTICE_TEXT`, `isPrivate`, `privateChanges`, Handlers.

- [ ] **Step 1: 실패 테스트**(renderToString·요소 props)
  - 요청 화면: 고지 문구와 체크 칸 `확인했어요`; 체크 전에는 `요청 전송` 버튼이 막힘(`disabled`); 체크하면 열림. 체크 칸은 `acknowledged` prop과 `onAcknowledge`.
  - 모드 화면: 고지를 확인하지 않았으면 모드 버튼이 막히고 "요청 화면에서 외부 전송 안내를 확인해 주세요." 안내.
  - 질문 카드: `🔒 이 답은 AI에 보내지 않기` 체크 칸, 기본값은 `isPrivate(session.private_names, question.field)`; 답을 보낼 때(선택·직접 입력) 체크 상태가 기본값과 다르거나 기본값이 true면 `private`를 싣는다 — 단순하게 언제나 `private: 체크 상태`를 싣는다.
  - 답 고치기 화면: 같은 체크 칸, 같은 방식.
  - 미확인 정보 입력: 항목마다 `AI에 보내지 않기` 체크 칸(기본값 `item.private`), 저장할 때 `privateChanges(처음, 지금)`.
  - 기준 표(확인 화면·결과 문서): `private` 행 옆에 `AI에 보내지 않음`. 내려받는 HTML에도 같은 표시.
- [ ] **Step 2: 실패 확인** — FAIL
- [ ] **Step 3: 구현** — 위 동작. CSS는 토큰만(체크 칸 줄 `.privacy-toggle`: 작은 글자·간격 토큰). `view.tsx`가 `state.notices`·`session.private_names`를 화면에 넘긴다(화면 모델에 `noticeAcknowledged`를 더하는 방식이면 `screenModel.ts`에서).
- [ ] **Step 4: 미리보기** — 프레임 추가: `request-notice`(고지 체크 전), `question-private`(정책 비공개 필드 질문, 체크된 상태), `confirm-private`(기준 표에 비공개 표시), `supplement-form`(기존 대화상자 프레임에 체크 칸이 보임). `frames.test.tsx` 목록을 맞춘다.
- [ ] **Step 5: 문서**
  - `README.md` "지금까지 된 것"에 "외부 AI로 보내기 전 보호(개인정보 자동 가림, 비공개 항목 제외, 외부 전송 고지·동의)". "남은 일" 표에 행 하나: `보안·개인정보` — 맡을 사람 `인수 기업` — 지금 상태 `보내기 전 거르기·고지 동의 동작(Mock)` — 상의할 점 `AI 업체의 데이터 보관·학습 정책과 계약, 개인정보 처리방침, 서버 DB 암호화, 로그인 뒤 보관 기간·삭제, 프롬프트 주입 대응, 자유 문장 속 비밀`.
  - `docs/HANDOFF.md`: "지금 상태" 표에 이 작업(PR 번호), "남겨 둔 것·알려진 한계"에 설계서 7절 4가지.
  - `CLAUDE.md` 하네스 원칙에 한 항목: "외부로 나가는 길목은 `_call`과 `illustrate` 두 곳이고, 둘 다 `privacy.masked_state`(비공개 이름의 값 → `[비공개 입력 · AI에 보내지 않음]`)로 렌더한 뒤 `privacy.outbound_prompt`(개인정보 가림)를 거친 프롬프트만 보내고 trace에 남긴다(`redactions` 개수). 세션 값은 그대로다. 비공개 이름 = 정책 `private_fields` + 사용자 설정 `private_overrides`(답·답 고치기·보완 정보 요청의 `private`). 비공개만 바뀌어도 결과는 최신 아님이다(`ResultVersion.private`). 세션은 외부 전송 고지 동의가 있어야 만든다(`notice_version`·`notice_acknowledged_at`)." 과제 하네스 정책 목록에 `private_fields`.
  - WBS: `scripts/wbs.py add 6.4 "외부 전송 보호(개인정보 가림·비공개·동의)" --after 6.3 --owner 개발 --start 2026-10-18 --end <완료일> --status 완료 --pct 1 --output "PR #<번호>"`(번호는 PR을 연 뒤), 기준일.
- [ ] **Step 6: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build`, `uv run --directory backend pytest -q` → PASS
- [ ] **Step 7: 커밋**

```bash
git add frontend README.md docs/HANDOFF.md CLAUDE.md
git commit -m "외부 전송 고지·비공개 체크 화면과 기준 표 표시, 미리보기 프레임, 문서"
```

## 브라우저 확인 (컨트롤러)

임시 SQLite DB로: 요청 화면에서 고지 체크 전 전송 막힘 → 체크 → 모드 → 질문 카드의 비공개 체크(정책 필드는 기본 체크) → 미확인 정보 입력에서 판매 가격 기본 체크 → 생성 → trace(`DEBUG=true`, `/sessions/{id}/trace`)의 generate 프롬프트에 비공개 값·전화번호가 없고 `[비공개 입력 · AI에 보내지 않음]`·`[전화번호]`가 있음 → 확인 화면·결과 문서에 "AI에 보내지 않음" 표시 → 비공개만 풀면 결과 최신 아님. 390px 넘침 없음, 새 프레임 스크롤 상자 없음.
