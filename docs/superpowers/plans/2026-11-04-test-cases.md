# 테스트 케이스(TC2·TC4~TC8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 수업 제출용 테스트 케이스를 "자동 테스트 + 엑셀 문서(`docs/TEST-CASES.xlsx`)" 두 가지로 만든다. 이번 PR은 TC2·TC4·TC5·TC6·TC7·TC8이고, TC1(프론트 반응 속도)·TC3(OpenAI vs Claude)은 문서에 '예정' 행만 둔다.

**Architecture:** 테스트 케이스마다 사용자 흐름을 API로 끝까지 따라가는 **인수 테스트**를 `backend/tests/acceptance/test_tcN_*.py`(프론트는 `frontend/src/acceptance/tc8.test.ts`)에 둔다. 공통 흐름 도우미는 `backend/tests/acceptance/flow.py` 하나다. 문서는 원본 `docs/test-cases.yaml`(사람이 고치는 곳)에서 `scripts/test_cases.py build`가 엑셀을 만들고, `run`이 실제로 테스트를 돌려 결과·통과 여부·실행일을 채운다. 원본의 자동 테스트 위치가 실제로 있는지는 백엔드 테스트(`tests/test_test_cases_doc.py`)가 확인한다(문서와 코드가 어긋나면 실패).

**Tech Stack:** pytest, FastAPI TestClient, MockProvider / vitest / openpyxl, PyYAML

## Global Constraints

- 모든 자동 테스트는 Mock(`MockProvider`)으로 돈다. 실제 AI 호출·비용 0.
- 인수 테스트는 HTTP API(`/api/v1/coaching/...`)로 사용자가 하는 순서를 따라간다. 내부 함수 직접 호출은 API로 관찰할 수 없는 것(하네스 객체 수, 저장소 재시작)에만 쓴다.
- 앱은 `create_app(provider=MockProvider(), ...)`, 클라이언트는 `tests.conftest.api_client(app, client_id=...)`. 남의 사용자는 `tests.conftest.OTHER_CLIENT_ID`.
- 기존 테스트는 고치지 않는다(새 파일만). 기존 동작이 계획과 다르면 테스트를 바꾸지 말고 보고한다(NEEDS_CONTEXT).
- 테스트 이름·docstring은 한국어로 무엇을 확인하는지 적는다(문서의 '확인 내용'과 같은 말).
- 커밋 메시지에 AI 공동저자·생성 표기를 넣지 않는다.
- 각 Task 끝에 `uv run --directory backend pytest -q` 전체 통과(프론트 Task는 `npm --prefix frontend test`·`npm --prefix frontend run build`도).

## 결정 사항

- **TC2 '외부 메모리 동적 참조'** = README '설계 고민 기록' 1번의 구조: (1) 요청은 무상태, 세션은 바깥 저장소에 있다(서버를 새로 띄워도 이어진다), (2) 하네스 파이프라인은 과제마다 한 번만 만들고 요청은 참조만 한다(요청 수와 무관), (3) AI 호출이 상한에 차도 넘치지(overflow) 않고 503으로 돌려보내며 가벼운 조회는 막히지 않는다.
- **TC5 'DB 생성 호출 상한'** = 세션 생성(DB에 새 작업이 생기는 요청)에도 AI 동시 호출 상한이 걸린다. 붐비면 503 + `Retry-After`이고 **DB에 작업이 생기지 않는다**. 동시에 여러 생성이 몰리면 성공한 수만큼만 저장된다.
- **TC6 '컨텍스트 메모리 모드별'** = 빠른·스탠다드·정밀 세션은 서로 독립(한 세션의 답이 다른 세션에 섞이지 않는다), 이어가기 컨텍스트는 모드와 상관없이 똑같이 들어간다, 질문 상한은 모드마다 정책값을 지킨다.
- **TC7 '다음 task 전송 오류'** = 이어가기의 실패 경로: 남의·없는 이전 작업 404, 결과 없는 이전 작업 404, 없는 버전 404, 버전 0은 422, AI 붐빔이면 503이고 새 작업이 생기지 않음, 가져온 내용 빼기, 비공개 유지.
- **TC8 '결과 생성 및 PDF 내보내기'** = 생성 → 결과(섹션·버전 1) → 저장 → 결과물 목록, 그리고 내려받는 문서(PDF는 인쇄용 HTML을 인쇄 창에 연다)에 제목·기준·섹션·인쇄 규칙이 들어가는지. 실제 'PDF로 저장' 창은 자동화할 수 없어 문서에 **수동 확인** 행으로 둔다.
- **실제 모델 확인에서 나온 것(2026-11-04, 렌더 Claude 1회)**: IR 결과 카드에 슬라이드 종류가 영어 이름(`cover —`)으로 나왔다. IR 생성 지침에 한국어 이름을 쓰라고 더한다(Task 6).

## File Structure

- Create `backend/tests/acceptance/flow.py` — 인수 테스트 공통 흐름(세션 시작·끝까지 답하기·생성)
- Create `backend/tests/acceptance/test_tc2_external_memory.py`
- Create `backend/tests/acceptance/test_tc4_task_harness.py`
- Create `backend/tests/acceptance/test_tc5_call_limit.py`
- Create `backend/tests/acceptance/test_tc6_mode_context.py`
- Create `backend/tests/acceptance/test_tc7_carry_errors.py`
- Create `backend/tests/acceptance/test_tc8_result.py`
- Create `frontend/src/acceptance/tc8.test.ts`
- Modify `backend/app/harness/tasks/ir_pitch/prompts/generate.md` — 슬라이드 종류 한국어 이름
- Create `docs/test-cases.yaml` — 테스트 케이스 원본
- Create `scripts/test_cases.py` — `build`(엑셀 만들기)·`run`(테스트 돌려 결과 채우기)
- Create `backend/tests/test_test_cases_doc.py` — 원본 형식과 자동 테스트 위치 확인
- Create `docs/TEST-CASES.xlsx` — 생성물(`run`으로 만든다)

---

### Task 1: 공통 흐름 도우미와 TC2(외부 메모리 동적 참조)

**Files:**
- Create: `backend/tests/acceptance/flow.py`
- Create: `backend/tests/acceptance/test_tc2_external_memory.py`

**Interfaces:**
- Produces (`tests.acceptance.flow`):
  - `BASE = "/api/v1/coaching"`
  - `start(client, task: str, raw: str = "한글 디자인 굿즈를 팔고 싶어요", mode: str = "standard", **extra) -> dict` — 세션을 만들고(201 확인) `SessionView` JSON을 돌려준다. `extra`는 요청 본문에 더한다(`from_session_id` 등).
  - `answer_all(client, view: dict, limit: int = 15) -> tuple[dict, list[str]]` — 걸린 질문이 없어질 때까지 자유 입력으로 답하고 (마지막 `SessionView`, 물어본 필드 이름 목록)을 돌려준다. `limit`번 넘게 묻으면 `AssertionError`.
  - `generate(client, session_id: str) -> dict` — 생성(200 확인) 후 `ResultView` JSON.
  - `finished(client, task: str, raw: str = ...) -> str` — 시작 → 끝까지 답 → 생성한 세션 id.

- [ ] **Step 1: Write the helper and the failing-first tests**

`backend/tests/acceptance/flow.py`:

```python
"""인수 테스트 공통 흐름: 사용자가 API로 하는 순서(시작 → 답하기 → 생성)를 그대로 따라간다."""
from fastapi.testclient import TestClient

BASE = "/api/v1/coaching"
DEFAULT_RAW = "한글 디자인 굿즈를 팔고 싶어요"


def start(client: TestClient, task: str, raw: str = DEFAULT_RAW, mode: str = "standard", **extra) -> dict:
    """세션을 만든다(외부 전송 안내 확인 포함). 201이 아니면 실패."""
    response = client.post(
        f"{BASE}/tasks/{task}/sessions",
        json={"notice_acknowledged": True, "raw_input": raw, "mode": mode, **extra},
    )
    assert response.status_code == 201, response.text
    return response.json()


def answer_all(client: TestClient, view: dict, limit: int = 15) -> tuple[dict, list[str]]:
    """걸린 질문이 없어질 때까지 자유 입력으로 답한다. (마지막 세션 화면, 물어본 필드 순서)."""
    asked: list[str] = []
    for step in range(limit):
        question = view["next_question"]
        if question is None:
            return view, asked
        asked.append(question["field"])
        response = client.post(
            f"{BASE}/sessions/{view['session_id']}/answers",
            json={"question_id": question["question_id"], "answer_type": "free_text", "value": f"테스트 답 {step + 1}"},
        )
        assert response.status_code == 200, response.text
        view = response.json()
    raise AssertionError(f"질문이 {limit}번 안에 끝나지 않았습니다: {asked}")


def generate(client: TestClient, session_id: str) -> dict:
    response = client.post(f"{BASE}/sessions/{session_id}/generate")
    assert response.status_code == 200, response.text
    return response.json()


def finished(client: TestClient, task: str, raw: str = DEFAULT_RAW) -> str:
    """시작 → 끝까지 답 → 생성까지 마친 세션 id."""
    view, _ = answer_all(client, start(client, task, raw))
    generate(client, view["session_id"])
    return view["session_id"]
```

`backend/tests/acceptance/test_tc2_external_memory.py`:

```python
"""TC2 외부 메모리 동적 참조: 요청은 무상태, 세션은 바깥 저장소, 파이프라인은 참조만, 상한에 차면 넘치지 않고 503."""
from app.core.store import SqliteSessionStore
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, generate, start
from tests.conftest import api_client


def test_tc2_1_세션은_바깥_저장소에_있어_서버를_새로_띄워도_이어진다(tmp_path):
    """앱 A에서 시작한 세션을 같은 DB 파일을 여는 새 앱 B에서 이어 답하고 생성한다."""
    path = tmp_path / "sessions.db"
    first = api_client(create_app(provider=MockProvider(), store=SqliteSessionStore(path)))
    view = start(first, "business_plan")
    question = view["next_question"]
    first.post(
        f"{BASE}/sessions/{view['session_id']}/answers",
        json={"question_id": question["question_id"], "answer_type": "free_text", "value": "선물 고르기가 어렵다"},
    )

    second = api_client(create_app(provider=MockProvider(), store=SqliteSessionStore(path)))
    resumed = second.get(f"{BASE}/sessions/{view['session_id']}").json()
    assert any(item["value"] == "선물 고르기가 어렵다" for item in resumed["summary"])
    resumed, _ = answer_all(second, resumed)
    assert generate(second, view["session_id"])["version"]["version"] == 1


def test_tc2_2_파이프라인은_과제마다_한_번만_만들고_요청은_참조만_한다():
    """세션을 많이 만들어도 하네스 객체는 과제 수(5)만큼이고 같은 객체를 쓴다."""
    app = create_app(provider=MockProvider())
    client = api_client(app)
    before = {h.task_type: id(h) for h in app.state.registry.all()}
    for i in range(20):
        start(client, ("business_plan", "product_planning", "branding", "marketing_content", "ir_pitch")[i % 5])
    after = {h.task_type: id(h) for h in app.state.registry.all()}
    assert len(after) == 5
    assert before == after


def test_tc2_3_AI_호출이_상한에_차도_넘치지_않고_503이며_조회는_막히지_않는다():
    """자리가 다 찬 동안 생성은 503(세션 그대로), 세션 목록·세션 조회는 바로 200."""
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    view = start(client, "branding")
    sid = view["session_id"]

    with slots.hold():
        busy = client.post(f"{BASE}/sessions/{sid}/generate")
        listed = client.get(f"{BASE}/sessions")
        shown = client.get(f"{BASE}/sessions/{sid}")

    assert busy.status_code == 503
    assert "retry-after" in busy.headers
    assert listed.status_code == 200 and [s["session_id"] for s in listed.json()] == [sid]
    assert shown.status_code == 200 and shown.json()["status"] == view["status"]
    assert shown.json()["has_result"] is False
```

`SqliteSessionStore`를 넘기고 `assets`를 넘기지 않으면 `create_app`이 설정(테스트에서는 memory)으로 파일 저장소를 만든다 — 문제가 되면 `assets=InMemoryAssetStore()`(`app.core.assets`)를 같이 넘긴다.

- [ ] **Step 2: Run tests**

Run: `uv run --directory backend pytest tests/acceptance -v`
Expected: 3 passed. (이 Task는 기존 동작을 문서화하는 인수 테스트라 구현 변경이 없다. 하나라도 실패하면 테스트 대상 동작이 결정 사항과 다르다는 뜻이므로 테스트를 억지로 맞추지 말고 NEEDS_CONTEXT로 보고한다. 단, 키 이름·도우미 사용 같은 테스트 쪽 실수는 고친다.)

인수 테스트가 실제로 무언가를 잡는지 한 번 확인한다: `test_tc2_1`에서 두 번째 앱에 `SqliteSessionStore(tmp_path / "other.db")`를 넘기면 실패해야 한다(확인 후 되돌린다). 이 확인을 보고서에 적는다.

- [ ] **Step 3: Full suite and commit**

Run: `uv run --directory backend pytest -q` → 전체 PASS

```bash
git add backend/tests/acceptance
git commit -m "TC2 인수 테스트: 외부 메모리 동적 참조(무상태·바깥 저장소·상한)"
```

---

### Task 2: TC4(하네스 파이프라인 과제별 적용)

**Files:**
- Create: `backend/tests/acceptance/test_tc4_task_harness.py`

**Interfaces:**
- Consumes: `tests.acceptance.flow` (`BASE`, `start`, `answer_all`, `generate`); `app.harness.registry.TASK_TYPES`; 각 과제 `content_model`(`app.state.registry.get(task).content_model`); `app.harness.validation`의 결과 모델은 쓰지 않는다(API로 본다).

- [ ] **Step 1: Write the tests**

```python
"""TC4 하네스 파이프라인 과제별 적용: 과제마다 다른 질문·결과 스키마·검증 규칙·질문 상한."""
import pytest

from app.core.results import GenerationResult, ResultCard, sections_from_cards
from app.core.state import SessionState
from app.harness.registry import TASK_TYPES
from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, generate, start
from tests.conftest import api_client


@pytest.fixture(scope="module")
def app():
    return create_app(provider=MockProvider())


@pytest.mark.parametrize("task", TASK_TYPES)
def test_tc4_1_과제마다_자기_정책의_질문을_묻고_자기_스키마로_결과를_낸다(app, task):
    client = api_client(app)
    policy = app.state.registry.get(task).policy
    view, asked = answer_all(client, start(client, task))
    assert asked, "질문이 하나도 없었습니다"
    assert set(asked) <= {f.name for f in policy.fields}
    result = generate(client, view["session_id"])
    app.state.registry.get(task).content_model.model_validate(result["result"]["content"])
    summary = next(s for s in client.get(f"{BASE}/sessions").json() if s["session_id"] == view["session_id"])
    assert summary["title"] == policy.title


@pytest.mark.parametrize(
    ("task", "expected_rules"),
    [
        ("business_plan", {"unsupported_market_claims"}),
        ("marketing_content", {"no_exaggeration"}),
        ("ir_pitch", {"unsupported_investor_claims"}),
        ("branding", set()),
        ("product_planning", set()),
    ],
)
def test_tc4_2_같은_문장도_과제마다_다른_금지_규칙으로_검사한다(app, task, expected_rules):
    """'예상 매출 100% 무조건'을 과제별 표현 규칙에 넣으면 그 과제 규칙만 걸린다."""
    harness = app.state.registry.get(task)
    card = ResultCard(card_type="diagnosis", title="t", body="b", order=1)
    result = GenerationResult(sections=sections_from_cards([card]), full_text="예상 매출 100% 무조건", content={})
    term_rules = {"unsupported_market_claims", "no_exaggeration", "unsupported_investor_claims", "naming_not_definitive"}
    hits = set()
    for check in harness.validators:
        for issue in check(SessionState(task_type=task), result, harness.policy):
            if issue.rule in term_rules:
                hits.add(issue.rule)
    assert hits == expected_rules


@pytest.mark.parametrize("task", TASK_TYPES)
@pytest.mark.parametrize("mode", ["quick", "standard", "precise"])
def test_tc4_3_과제마다_모드별_질문_상한을_지킨다(app, task, mode):
    client = api_client(app)
    cap = app.state.registry.get(task).policy.question_caps[mode]
    _, asked = answer_all(client, start(client, task, mode=mode))
    assert len(set(asked)) <= cap
```

검증 규칙 이름은 각 과제 `validators.py`에서 확인한다. `branding`의 `naming_not_definitive`나 `product_planning`의 규칙이 이 문장에 걸리면(그 과제 규칙의 실제 동작) 기대값을 실제 규칙 이름으로 바꾸고, 바꾼 이유를 보고서에 적는다 — 확인하려는 것은 "과제마다 다른 규칙 묶음이 적용된다"이다. `content`가 빈 사전이라 `content`를 읽는 규칙(예: 마케팅 `cta_present`, IR `ask_present`·`core_slides`)도 이슈를 내므로 위처럼 표현 규칙 이름만 모아 비교한다.

- [ ] **Step 2: Run tests** — `uv run --directory backend pytest tests/acceptance/test_tc4_task_harness.py -v` → 모두 PASS(Task 1과 같은 원칙: 동작이 결정 사항과 다르면 NEEDS_CONTEXT).

- [ ] **Step 3: Full suite and commit**

```bash
git add backend/tests/acceptance/test_tc4_task_harness.py
git commit -m "TC4 인수 테스트: 하네스 파이프라인 과제별 적용"
```

---

### Task 3: TC5(DB 생성 호출 상한)

**Files:**
- Create: `backend/tests/acceptance/test_tc5_call_limit.py`

**Interfaces:**
- Consumes: `tests.acceptance.flow` (`BASE`, `start`); `app.providers.limit.CallSlots`; `app.providers.mock.MockProvider`; `app.core.store.InMemorySessionStore`

- [ ] **Step 1: Write the tests**

```python
"""TC5 DB 생성 호출 상한: 세션 생성(진단 AI 호출 포함)에도 동시 호출 상한이 걸리고, 붐비면 DB에 작업이 생기지 않는다."""
import threading
import time

from app.core.store import InMemorySessionStore
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, start
from tests.conftest import api_client

BODY = {"notice_acknowledged": True, "raw_input": "향초"}


class SlowProvider(MockProvider):
    """AI 호출이 오래 걸리는 상황(실제 모델)을 흉내 낸다."""

    def complete(self, *args, **kwargs):
        time.sleep(0.3)
        return super().complete(*args, **kwargs)


def test_tc5_1_붐비면_세션_생성은_503이고_DB에_작업이_생기지_않는다():
    slots = CallSlots(size=1, wait_seconds=0)
    store = InMemorySessionStore()
    client = api_client(create_app(provider=MockProvider(), store=store, slots=slots))
    with slots.hold():
        response = client.post(f"{BASE}/tasks/product_planning/sessions", json=BODY)
    assert response.status_code == 503
    assert response.headers["retry-after"] == "5"
    assert client.get(f"{BASE}/sessions").json() == []


def test_tc5_2_자리가_나면_같은_요청이_성공해_한_건만_저장된다():
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    with slots.hold():
        assert client.post(f"{BASE}/tasks/product_planning/sessions", json=BODY).status_code == 503
    view = start(client, "product_planning", "향초")
    assert [s["session_id"] for s in client.get(f"{BASE}/sessions").json()] == [view["session_id"]]


def test_tc5_3_동시에_몰리면_상한만큼만_통과하고_성공한_수만큼만_저장된다():
    """자리 2개·대기 0초에서 6개가 동시에 오면 일부는 503, 저장된 작업 수 = 201 응답 수."""
    slots = CallSlots(size=2, wait_seconds=0)
    app = create_app(provider=SlowProvider(), slots=slots)
    codes: list[int] = []
    lock = threading.Lock()

    def create() -> None:
        code = api_client(app).post(f"{BASE}/tasks/product_planning/sessions", json=BODY).status_code
        with lock:
            codes.append(code)

    threads = [threading.Thread(target=create) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sorted(set(codes)) <= [201, 503]
    assert 1 <= codes.count(201) <= 6 and codes.count(503) >= 1
    saved = api_client(app).get(f"{BASE}/sessions").json()
    assert len(saved) == codes.count(201)
```

`MockProvider.complete`의 실제 메서드 이름·시그니처는 `app/providers/mock.py`와 `app/providers/base.py`(`LLMProvider`)에서 확인해 `SlowProvider`가 같은 메서드를 덮게 한다. 6개 동시 요청에서 503이 하나도 안 나오면(스레드가 순서대로 돌았을 때) 0.3초 지연을 늘리지 말고, `threading.Barrier(6)`로 모든 스레드가 같이 요청을 보내게 해서 안정화한다. 테스트가 1초를 넘지 않게 한다. TestClient를 스레드마다 새로 만드는 것은 같은 `app`(같은 상한·같은 저장소)을 공유한다.

- [ ] **Step 2: Run tests** — `uv run --directory backend pytest tests/acceptance/test_tc5_call_limit.py -v` 를 5번 반복해 매번 PASS(흔들림 없음)를 확인하고 보고서에 적는다: `for i in 1 2 3 4 5; do uv run --directory backend pytest tests/acceptance/test_tc5_call_limit.py -q || break; done`

- [ ] **Step 3: Full suite and commit**

```bash
git add backend/tests/acceptance/test_tc5_call_limit.py
git commit -m "TC5 인수 테스트: 세션 생성에도 AI 동시 호출 상한"
```

---

### Task 4: TC6(모드별 컨텍스트)·TC7(이어가기 오류)

**Files:**
- Create: `backend/tests/acceptance/test_tc6_mode_context.py`
- Create: `backend/tests/acceptance/test_tc7_carry_errors.py`

**Interfaces:**
- Consumes: `tests.acceptance.flow` (`BASE`, `start`, `answer_all`, `generate`, `finished`); `tests.conftest.api_client`, `OTHER_CLIENT_ID`; `app.providers.limit.CallSlots`; `app.core.messages`의 `PREVIOUS_SESSION_NOT_FOUND_MESSAGE`, `RESULT_NOT_READY_MESSAGE`, `VERSION_NOT_FOUND_MESSAGE`, `AI_BUSY_MESSAGE`

- [ ] **Step 1: Write TC6**

```python
"""TC6 컨텍스트 메모리 모드별: 모드가 다른 세션은 서로 독립, 이어가기 컨텍스트는 모드와 상관없이 같다."""
import pytest

from app.main import create_app
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, answer_all, finished, start
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
        question = view["next_question"]
        client.post(
            f"{BASE}/sessions/{view['session_id']}/answers",
            json={"question_id": question["question_id"], "answer_type": "free_text", "value": f"{mode} 전용 답"},
        )
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


def test_tc6_3_모드마다_질문_상한이_다르게_적용된다(client):
    caps = {"quick": 3, "standard": 5, "precise": 10}
    for mode in MODES:
        _, asked = answer_all(client, start(client, "business_plan", mode=mode))
        assert len(set(asked)) <= caps[mode]
    _, quick = answer_all(client, start(client, "business_plan", mode="quick"))
    _, precise = answer_all(client, start(client, "business_plan", mode="precise"))
    assert len(set(quick)) <= len(set(precise))
```

(`caps`는 `business_plan/policy.yaml`의 `question_caps`와 같다. 다르면 정책값을 따른다.)

- [ ] **Step 2: Write TC7**

```python
"""TC7 다음 과제로 이어가기 오류: 실패해도 새 작업이 잘못 생기지 않고, 가져온 값은 빼거나 비공개로 지킨다."""
import pytest

from app.core.messages import (
    AI_BUSY_MESSAGE,
    PREVIOUS_SESSION_NOT_FOUND_MESSAGE,
    RESULT_NOT_READY_MESSAGE,
    VERSION_NOT_FOUND_MESSAGE,
)
from app.main import create_app
from app.providers.limit import CallSlots
from app.providers.mock import MockProvider
from tests.acceptance.flow import BASE, finished, start
from tests.conftest import OTHER_CLIENT_ID, api_client


def create(client, **extra):
    return client.post(
        f"{BASE}/tasks/ir_pitch/sessions",
        json={"notice_acknowledged": True, "raw_input": "투자 발표 준비", **extra},
    )


def session_ids(client) -> list[str]:
    return [s["session_id"] for s in client.get(f"{BASE}/sessions").json()]


@pytest.fixture
def app():
    return create_app(provider=MockProvider())


def test_tc7_1_남의_이전_작업이나_없는_작업은_404이고_새_작업이_생기지_않는다(app):
    mine = api_client(app)
    prev = finished(mine, "business_plan")
    other = api_client(app, client_id=OTHER_CLIENT_ID)
    for client, source in ((other, prev), (mine, "sess_없는작업")):
        before = session_ids(client)
        response = create(client, from_session_id=source)
        assert (response.status_code, response.json()) == (404, {"detail": PREVIOUS_SESSION_NOT_FOUND_MESSAGE})
        assert session_ids(client) == before


def test_tc7_2_결과가_없는_이전_작업은_404(app):
    client = api_client(app)
    prev = start(client, "business_plan")["session_id"]
    response = create(client, from_session_id=prev)
    assert (response.status_code, response.json()) == (404, {"detail": RESULT_NOT_READY_MESSAGE})


def test_tc7_3_없는_버전은_404_버전_0은_422(app):
    client = api_client(app)
    prev = finished(client, "business_plan")
    missing = create(client, from_session_id=prev, from_version=9)
    assert (missing.status_code, missing.json()) == (404, {"detail": VERSION_NOT_FOUND_MESSAGE})
    assert create(client, from_session_id=prev, from_version=0).status_code == 422


def test_tc7_4_AI가_붐비면_503이고_새_작업이_생기지_않는다():
    slots = CallSlots(size=1, wait_seconds=0)
    client = api_client(create_app(provider=MockProvider(), slots=slots))
    prev = finished(client, "business_plan")
    before = session_ids(client)
    with slots.hold():
        response = create(client, from_session_id=prev)
    assert (response.status_code, response.json()) == (503, {"detail": AI_BUSY_MESSAGE})
    assert session_ids(client) == before


def test_tc7_5_가져온_내용을_빼면_이전_과제_값이_사라진다(app):
    client = api_client(app)
    prev = finished(client, "business_plan", "한글 디자인 북백 사업")
    view = start(client, "ir_pitch", "투자 발표 준비", from_session_id=prev)
    assert any(item["source"] == "previous_task" for item in view["summary"])
    cleared = client.delete(f"{BASE}/sessions/{view['session_id']}/context")
    assert cleared.status_code == 200
    assert all(item["source"] != "previous_task" for item in cleared.json()["summary"])
    assert cleared.json()["context"] is None


def test_tc7_6_이전_과제에서_비공개였던_값은_새_과제에서도_비공개다(app):
    """사업계획의 수익모델은 기본 비공개다. IR의 수익 구조로 넘어와도 비공개로 남는다."""
    client = api_client(app)
    view = start(client, "business_plan", "한글 디자인 북백 사업", mode="precise")
    for _ in range(15):
        question = view["next_question"]
        if question is None:
            break
        value = "제품 판매" if question["field"] == "revenue_model" else "테스트 답"
        view = client.post(
            f"{BASE}/sessions/{view['session_id']}/answers",
            json={"question_id": question["question_id"], "answer_type": "free_text", "value": value},
        ).json()
    client.post(f"{BASE}/sessions/{view['session_id']}/generate")
    carried = start(client, "ir_pitch", "투자 발표 준비", from_session_id=view["session_id"])
    if any(item["field"] == "business_model" and item["source"] == "previous_task" for item in carried["summary"]):
        assert "business_model" in carried["private_names"]
    else:
        pytest.fail("수익모델이 이어지지 않았습니다(사업계획에서 revenue_model을 묻지 않았다면 답 흐름을 확인)")
```

`test_tc7_5`에서 `DELETE …/context` 뒤의 `context` 값(None인지, 표시만 빠지는지)은 `CLAUDE.md` "다음 과제로 이어가기" 설명과 `tests/test_api_carry.py::test_delete_context_removes_carried_values_and_is_idempotent`를 보고 실제 계약에 맞춘다. `test_tc7_6`에서 사업계획이 precise 모드에서도 `revenue_model`을 묻지 않는다면(준비도로 일찍 멈춤) `tests/test_ir_pitch.py::test_private_revenue_model_stays_private_when_carried_into_ir_pitch`처럼 저장소에 사실을 넣는 방식 대신, 사업계획 세션에 `POST /sessions/{id}/continue`로 남은 질문을 이어 받아 답한다. 그래도 묻지 않으면 NEEDS_CONTEXT로 보고한다(`pytest.fail` 분기를 지우고 확정된 흐름으로 쓴다 — 최종 테스트에 조건 분기를 남기지 않는다).

- [ ] **Step 3: Run tests** — `uv run --directory backend pytest tests/acceptance/test_tc6_mode_context.py tests/acceptance/test_tc7_carry_errors.py -v` → PASS

- [ ] **Step 4: Full suite and commit**

```bash
git add backend/tests/acceptance/test_tc6_mode_context.py backend/tests/acceptance/test_tc7_carry_errors.py
git commit -m "TC6·TC7 인수 테스트: 모드별 컨텍스트, 이어가기 오류"
```

---

### Task 5: TC8(결과 생성 및 PDF 내보내기)

**Files:**
- Create: `backend/tests/acceptance/test_tc8_result.py`
- Create: `frontend/src/acceptance/tc8.test.ts`

**Interfaces:**
- Consumes (backend): `tests.acceptance.flow`; API `POST /sessions/{id}/versions/{n}/save`, `GET /sessions`(`saved_versions`), `GET /sessions/{id}/result`
- Consumes (frontend): `frontend/src/app/documentFile.ts`(화면 모델 → `DocumentFile`), `frontend/src/lib/documentHtml.ts`의 `documentHtml(content)`, `frontend/src/lib/documentDocx.ts`의 `documentDocx(content)`, `frontend/src/lib/documentFormats.ts`의 `fileName`, `frontend/src/testing/factories.ts`의 `makeResult` 등. 정확한 함수 이름·인자는 각 파일과 기존 테스트(`documentFile.test.ts`, `documentHtml.test.ts`, `documentDocx.test.ts`)에서 확인한다.

- [ ] **Step 1: Write backend TC8**

```python
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
```

버전 번호 키는 `VersionSummary.version`이다.

- [ ] **Step 2: Write frontend TC8**

`frontend/src/acceptance/tc8.test.ts` — 결과 화면 모델에서 내려받는 문서를 만들고, 형식별 변환 결과를 확인한다. 기존 테스트의 픽스처 만들기 방식을 그대로 쓴다:

```ts
import { describe, expect, it } from "vitest";
// 아래 import 경로·이름은 frontend/src/app/documentFile.test.ts 와 lib/documentHtml.test.ts, lib/documentDocx.test.ts 가 쓰는 것과 같게 맞춘다.

describe("TC8 결과 내보내기", () => {
  it("TC8-3 결과 화면에서 내려받는 문서 이름은 '{작업 이름}_V{n}'이다", () => {
    // documentFile.test.ts와 같은 방법으로 결과 화면 모델을 만들고 DocumentFile을 얻는다.
    // expect(file.basename).toBe("<작업 이름>_V1");
  });

  it("TC8-4 PDF로 여는 인쇄용 HTML에 제목·기준·섹션 본문·인쇄 규칙이 들어간다", () => {
    // const html = documentHtml(file.content);
    // expect(html).toContain(<결과 제목>); expect(html).toContain(<기준 라벨>); expect(html).toContain(<섹션 본문>);
    // expect(html).toMatch(/@page|@media print/);
  });

  it("TC8-5 Word(.docx) 문서에도 같은 섹션 제목이 들어간다", async () => {
    // documentDocx.test.ts가 docx 내용을 읽는 방법(Packer + jszip)으로 document.xml을 열어 섹션 제목을 확인한다.
  });

  it("TC8-6 HTML 파일 이름 확장자는 형식을 따른다", () => {
    // expect(fileName("작업_V1", "html")).toBe("작업_V1.html"); docx도 같다.
  });
});
```

주석은 지침이다 — 최종 파일에는 실제 단언을 쓰고 주석을 남기지 않는다. 각 단언은 기존 단위 테스트를 복사하지 말고 "결과 화면 모델 하나에서 시작해 세 형식까지" 한 흐름으로 잇는다(같은 `file`을 세 형식에 쓴다). PDF 인쇄 창 자체(`exportDocument('pdf')`)는 브라우저 DOM이 필요해 자동화하지 않는다(문서의 수동 행 TC8-7).

- [ ] **Step 3: Run tests**

Run: `uv run --directory backend pytest tests/acceptance/test_tc8_result.py -v`, `npm --prefix frontend test -- tc8`
Expected: PASS

- [ ] **Step 4: Full suites, build, commit**

Run: `uv run --directory backend pytest -q`, `npm --prefix frontend test`, `npm --prefix frontend run build`

```bash
git add backend/tests/acceptance/test_tc8_result.py frontend/src/acceptance
git commit -m "TC8 인수 테스트: 결과 생성·저장과 문서 내보내기"
```

---

### Task 6: IR 슬라이드 종류를 한국어 이름으로

**Files:**
- Modify: `backend/app/harness/tasks/ir_pitch/prompts/generate.md`
- Test: `backend/tests/test_ir_pitch.py`

**Interfaces:**
- Consumes: `HarnessRegistry(MockProvider()).get("ir_pitch").prompts.render("generate", **values)` — 렌더 방법은 `tests/test_tasks.py::test_every_stage_template_renders`를 따른다(`context_keys("generate")`의 키만 넘긴다).

- [ ] **Step 1: Write the failing test**

```python
SLIDE_NAMES = {
    "cover": "표지", "problem": "문제", "solution": "해결", "market": "시장", "business_model": "비즈니스 모델",
    "traction": "성과", "competition": "경쟁", "team": "팀", "financials": "재무 계획", "ask": "투자 요청",
}


def test_generate_prompt_tells_korean_slide_names(harness):
    """실제 모델이 카드에 'cover —'처럼 영어 종류를 쓴 적이 있다(2026-11-04). 화면에는 한국어 이름을 쓰게 한다."""
    system = render_generate_system(harness)  # test_tasks.py의 렌더 방식으로 system 블록을 얻는 작은 도우미를 이 파일에 둔다
    for english, korean in SLIDE_NAMES.items():
        assert f"{english}={korean}" in system
```

- [ ] **Step 2: Run** — `uv run --directory backend pytest tests/test_ir_pitch.py -k korean -v` → FAIL

- [ ] **Step 3: Implement** — `generate.md`의 IR 지침 중 슬라이드를 카드에 싣는 줄 바로 다음에 한 줄을 더한다(정적 문구, 빈 줄 두 개 연속 금지):

```
- 카드에 쓰는 슬라이드 종류는 한국어 이름으로 쓴다: cover=표지, problem=문제, solution=해결, market=시장, business_model=비즈니스 모델, traction=성과, competition=경쟁, team=팀, financials=재무 계획, ask=투자 요청. slides의 slide_type 값은 영어 그대로 둔다.
```

- [ ] **Step 4: Run** — `uv run --directory backend pytest tests/test_ir_pitch.py tests/test_tasks.py -q` → PASS, 그다음 전체.

- [ ] **Step 5: Commit**

```bash
git add backend/app/harness/tasks/ir_pitch/prompts/generate.md backend/tests/test_ir_pitch.py
git commit -m "IR 결과 카드의 슬라이드 종류를 한국어 이름으로"
```

---

### Task 7: 테스트 케이스 문서(원본 YAML → 엑셀)와 결과 채우기

**Files:**
- Create: `docs/test-cases.yaml`
- Create: `scripts/test_cases.py`
- Create: `backend/tests/test_test_cases_doc.py`
- Create: `docs/TEST-CASES.xlsx` (생성물)

**Interfaces:**
- Produces:
  - `docs/test-cases.yaml` 형식(최상위 `cases:` 목록). 항목 키: `id`(예 `TC5-1`), `group`(예 `TC5`), `item`(요구사항 원문, 예 "db 생성 호출 상한 적용 되는지"), `title`, `precondition`, `steps`(문자열 목록), `expected`, `method`(`자동`|`수동`|`예정`), `tests`(자동일 때만, 문자열 목록: `backend:tests/acceptance/test_tc5_call_limit.py::test_tc5_1_…` 또는 `frontend:src/acceptance/tc8.test.ts::TC8-4 …`), `note`(선택).
  - `scripts/test_cases.py`:
    - `load_cases(path: Path) -> list[Case]` — YAML을 읽어 검증(모르는 키 거부, `method`가 `자동`이면 `tests` 1개 이상, `id` 중복 금지). `Case`는 pydantic 모델(`extra="forbid"`).
    - `build(cases: list[Case], results: dict[str, str], ran_on: str | None, out: Path) -> None` — 엑셀 한 시트 '테스트 케이스'. 열: `ID, 요구사항, 테스트 케이스, 사전 조건, 절차, 기대 결과, 방식, 자동 테스트 위치, 실제 결과, 통과, 실행일, 비고`. `results`는 `id → "통과"|"실패"`(없으면 빈칸; 수동·예정은 빈칸). 첫 행 고정, 열 너비·줄바꿈 설정, 머리글 굵게.
    - `case_results(cases, outcomes: dict[str, bool]) -> dict[str, str]` — [순수] 각 케이스의 테스트 참조 결과를 모아 하나라도 실패면 "실패", 모두 통과면 "통과".
    - CLI: `build`(결과 없이 엑셀), `run`(백엔드 `uv run --directory backend pytest <참조 파일들> --junitxml=<임시>`와 프론트 `npm --prefix frontend exec vitest run <참조 파일들> -- --reporter=json --outputFile=<임시>`를 돌려 참조별 통과 여부를 읽고 `build`).
  - `backend/tests/test_test_cases_doc.py` — 원본이 형식대로이고, 모든 `backend:` 참조의 파일이 있고 그 함수가 정의돼 있으며, 모든 `frontend:` 참조의 파일이 있고 그 테스트 이름 문자열이 들어 있는지 확인. 원본 그룹이 TC1~TC8을 모두 가지는지도 확인.

- [ ] **Step 1: Write the failing doc test**

```python
"""테스트 케이스 문서 원본(docs/test-cases.yaml)이 형식대로이고, 적힌 자동 테스트가 실제로 있다."""
import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("test_cases_script", ROOT / "scripts" / "test_cases.py")
script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(script)

CASES = script.load_cases(ROOT / "docs" / "test-cases.yaml")


def test_every_requirement_group_is_present():
    assert {c.group for c in CASES} == {f"TC{n}" for n in range(1, 9)}


def test_backend_references_point_to_defined_tests():
    for case in CASES:
        for ref in case.tests:
            side, target = ref.split(":", 1)
            if side != "backend":
                continue
            file, name = target.split("::")
            path = ROOT / "backend" / file
            assert path.exists(), f"{case.id}: {file} 없음"
            names = {n.name for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))) if isinstance(n, ast.FunctionDef)}
            assert name.split("[")[0] in names, f"{case.id}: {name} 없음"


def test_frontend_references_point_to_existing_test_titles():
    for case in CASES:
        for ref in case.tests:
            side, target = ref.split(":", 1)
            if side != "frontend":
                continue
            file, title = target.split("::")
            path = ROOT / "frontend" / file
            assert path.exists(), f"{case.id}: {file} 없음"
            assert title in path.read_text(encoding="utf-8"), f"{case.id}: '{title}' 없음"


def test_case_results_fail_if_any_reference_fails():
    cases = [c for c in CASES if c.tests][:1]
    ok = {ref: True for ref in cases[0].tests}
    assert script.case_results(cases, ok) == {cases[0].id: "통과"}
    bad = {**ok, cases[0].tests[0]: False}
    assert script.case_results(cases, bad) == {cases[0].id: "실패"}


def test_build_writes_header_and_one_row_per_case(tmp_path):
    from openpyxl import load_workbook

    out = tmp_path / "tc.xlsx"
    script.build(CASES, {}, None, out)
    sheet = load_workbook(out)["테스트 케이스"]
    header = [c.value for c in sheet[1]]
    assert header[:3] == ["ID", "요구사항", "테스트 케이스"]
    assert sheet.max_row == len(CASES) + 1
```

`openpyxl`·`pyyaml`이 백엔드 테스트 환경에 없으면(`uv run --directory backend python -c "import openpyxl, yaml"`), `yaml`은 이미 정책 읽기에 쓰므로 있고, `openpyxl`은 `backend/pyproject.toml`의 개발 의존성(dev 그룹)에 더한다(`uv add --directory backend --dev openpyxl`). `uv.lock` 변경도 커밋한다.

- [ ] **Step 2: Run** — `uv run --directory backend pytest tests/test_test_cases_doc.py -v` → FAIL(스크립트·원본 없음)

- [ ] **Step 3: Write `scripts/test_cases.py`**

```python
"""테스트 케이스 문서: 원본 docs/test-cases.yaml → docs/TEST-CASES.xlsx.

  build  결과 칸을 비운 엑셀을 만든다
  run    자동 테스트를 실제로 돌려 실제 결과·통과·실행일을 채운다

uv run --directory backend python ../scripts/test_cases.py run
"""
import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "test-cases.yaml"
OUTPUT = ROOT / "docs" / "TEST-CASES.xlsx"
HEADER = ["ID", "요구사항", "테스트 케이스", "사전 조건", "절차", "기대 결과", "방식", "자동 테스트 위치", "실제 결과", "통과", "실행일", "비고"]
WIDTHS = [9, 22, 34, 26, 48, 40, 7, 52, 10, 7, 12, 30]


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    group: str
    item: str
    title: str
    precondition: str = ""
    steps: list[str] = Field(min_length=1)
    expected: str
    method: Literal["자동", "수동", "예정"]
    tests: list[str] = Field(default_factory=list)
    note: str = ""

    @model_validator(mode="after")
    def _tests_match_method(self) -> "Case":
        if self.method == "자동" and not self.tests:
            raise ValueError(f"{self.id}: 자동 케이스에는 tests가 필요합니다")
        if self.method != "자동" and self.tests:
            raise ValueError(f"{self.id}: 수동·예정 케이스에는 tests를 적지 않습니다")
        return self


def load_cases(path: Path) -> list[Case]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    cases = [Case.model_validate(c) for c in data["cases"]]
    ids = [c.id for c in cases]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"테스트 케이스 ID가 중복됩니다: {', '.join(repeated)}")
    return cases


def case_results(cases: list[Case], outcomes: dict[str, bool]) -> dict[str, str]:
    """[순수] 참조 테스트가 모두 통과면 '통과', 하나라도 실패·없음이면 '실패'. 자동 케이스만."""
    return {
        c.id: "통과" if all(outcomes.get(ref, False) for ref in c.tests) else "실패"
        for c in cases
        if c.method == "자동"
    }


def build(cases: list[Case], results: dict[str, str], ran_on: str | None, out: Path) -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "테스트 케이스"
    sheet.append(HEADER)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    for c in cases:
        result = results.get(c.id, "")
        sheet.append([
            c.id, c.item, c.title, c.precondition,
            "\n".join(f"{i}. {s}" for i, s in enumerate(c.steps, 1)),
            c.expected, c.method, "\n".join(c.tests),
            result, "O" if result == "통과" else ("X" if result == "실패" else ""),
            ran_on if result else "", c.note,
        ])
    for i, width in enumerate(WIDTHS, 1):
        sheet.column_dimensions[sheet.cell(1, i).column_letter].width = width
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    sheet.freeze_panes = "A2"
    book.save(out)


def _backend_outcomes(refs: list[str], tmp: Path) -> dict[str, bool]:
    if not refs:
        return {}
    report = tmp / "backend.xml"
    files = sorted({r.removeprefix("backend:").split("::")[0] for r in refs})
    subprocess.run(["uv", "run", "--directory", str(ROOT / "backend"), "pytest", *files, f"--junitxml={report}", "-q"], check=False)
    passed: dict[str, bool] = {}
    for case in ET.parse(report).iter("testcase"):
        name = case.get("name", "").split("[")[0]
        ok = not any(child.tag in ("failure", "error", "skipped") for child in case)
        passed[name] = passed.get(name, True) and ok
    return {r: passed.get(r.split("::")[1].split("[")[0], False) for r in refs}


def _frontend_outcomes(refs: list[str], tmp: Path) -> dict[str, bool]:
    if not refs:
        return {}
    report = tmp / "frontend.json"
    files = sorted({r.removeprefix("frontend:").split("::")[0] for r in refs})
    subprocess.run(
        ["npm", "--prefix", str(ROOT / "frontend"), "exec", "--", "vitest", "run", *files, "--reporter=json", f"--outputFile={report}"],
        check=False, shell=sys.platform == "win32",
    )
    data = json.loads(report.read_text(encoding="utf-8"))
    passed = {
        a["title"]: a["status"] == "passed"
        for result in data["testResults"]
        for a in result["assertionResults"]
    }
    return {r: passed.get(r.split("::")[1], False) for r in refs}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "run"])
    args = parser.parse_args()
    cases = load_cases(SOURCE)
    if args.command == "build":
        build(cases, {}, None, OUTPUT)
    else:
        refs = [r for c in cases for r in c.tests]
        with tempfile.TemporaryDirectory() as tmp:
            outcomes = {
                **_backend_outcomes([r for r in refs if r.startswith("backend:")], Path(tmp)),
                **_frontend_outcomes([r for r in refs if r.startswith("frontend:")], Path(tmp)),
            }
        build(cases, case_results(cases, outcomes), date.today().isoformat(), OUTPUT)
    print(f"저장: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

vitest 파일 경로는 `frontend/` 기준 상대 경로(`src/acceptance/tc8.test.ts`)다. Windows에서 `npm`은 `npm.cmd`라 `shell=True`가 필요하다(위 코드). vitest JSON의 `assertionResults[].title`이 `it(...)` 제목과 같은지 실제로 한 번 돌려 확인하고, 다르면(예: `fullName`) 맞춘다.

- [ ] **Step 4: Write `docs/test-cases.yaml`**

Task 1~5의 인수 테스트 함수마다 한 케이스, 거기에 수동·예정 행을 더한다. 형식 예(나머지도 같은 형식으로 모두 채운다):

```yaml
# 테스트 케이스 원본. 고친 뒤: uv run --directory backend python ../scripts/test_cases.py run
cases:
  - id: TC1-1
    group: TC1
    item: 프론트엔드 수정 후 최적화(리액트 반응 속도 0.5ms 이하)
    title: 버튼을 눌러 다음 화면으로 넘어갈 때 상태 갱신과 화면 판단이 0.5ms 이하
    precondition: 화면 상태·응답 데이터는 미리 준비(네트워크 제외)
    steps: [화면마다 이동 버튼에 해당하는 동작으로 reducer와 화면 모델을 계산한다, 반복 측정해 중앙값을 잰다]
    expected: 화면 전환 하나의 계산 시간 중앙값 0.5ms 이하
    method: 예정
    note: PR #38에서 자동 테스트로 바꾼다
  - id: TC2-1
    group: TC2
    item: 외부 메모리 참조 동적 연결(스레드 참조 전송 정의)
    title: 세션은 서버 메모리가 아니라 바깥 저장소에 있어 서버를 새로 띄워도 이어진다
    precondition: 같은 SQLite 파일을 여는 서버 두 개(A, B)
    steps:
      - A에서 사업계획 세션을 만들고 첫 질문에 답한다
      - 같은 DB를 여는 새 서버 B로 세션을 조회한다
      - B에서 남은 질문에 답하고 결과를 만든다
    expected: B에서 A의 답이 보이고, 이어서 답한 뒤 결과 버전 1이 생긴다
    method: 자동
    tests: ["backend:tests/acceptance/test_tc2_external_memory.py::test_tc2_1_세션은_바깥_저장소에_있어_서버를_새로_띄워도_이어진다"]
    note: README '설계 고민 기록' 1번(요청 상한 시 오버플로우를 외부 메모리 동적 참조로 해결)
  - id: TC3-1
    group: TC3
    item: api 테스트(오픈 ai vs 클로드) == 비용 발생
    title: 같은 평가 시나리오를 OpenAI·Claude로 돌려 시간·토큰·비용·결과 품질 비교
    steps: [scripts/measure.py로 두 제공자를 같은 시나리오로 돌린다(예산 상한 $5), 결과 표를 비교한다]
    expected: 두 제공자 모두 시나리오를 끝까지 완료하고 비교 표가 남는다
    method: 예정
    note: PR #39(실제 호출, 실행 전 승인)
  - id: TC8-7
    group: TC8
    item: 결과 생성 및 pdf 내보내기
    title: 실제 브라우저에서 PDF로 저장
    precondition: 결과가 있는 세션의 결과 화면
    steps: ['문서 내려받기 → PDF를 누른다', "인쇄 창에서 'PDF로 저장'을 고른다", 저장한 PDF를 연다]
    expected: 제목·반영한 기준·섹션 본문이 PDF에 그대로 있고 파일 이름이 '{작업 이름}_V{n}'이다
    method: 수동
    note: 인쇄 창은 자동화 브라우저에서 열린 채 멈춰 자동 테스트에서 뺐다
```

TC2-2·2-3, TC4-1~4-3, TC5-1~5-3, TC6-1~6-3, TC7-1~7-6, TC8-1·8-2(백엔드)·8-3~8-6(프론트)을 각 테스트에 맞춰 채운다. `parametrize` 테스트는 함수 이름만 적는다(모든 매개변수가 통과해야 통과). `item`은 사용자 요구사항 원문을 그대로 쓴다:
- TC1 "프론트엔드 수정 후 최적화(리액트 반응 속도 0.5ms 이하)"
- TC2 "외부 메모리 참조 동적 연결(스레드 참조 전송 정의)"
- TC3 "api 테스트(오픈 ai vs 클로드) == 비용 발생"
- TC4 "하네스 파이프라인 각 task 별 적용"
- TC5 "db 생성 호출 상한 적용 되는지"
- TC6 "컨텍스트 메모리 각 코칭 모드별로 따로 적용되는지"
- TC7 "컨텍스트 메모리 다음 task시 전송 오류"
- TC8 "결과 생성 및 pdf 내보내기"

- [ ] **Step 5: Run doc test and generate the workbook**

Run: `uv run --directory backend pytest tests/test_test_cases_doc.py -v` → PASS
Run: `uv run --directory backend python ../scripts/test_cases.py run` → `docs/TEST-CASES.xlsx` 저장, 자동 케이스가 모두 '통과'인지 `uv run --directory backend python -c "from openpyxl import load_workbook; s=load_workbook('../docs/TEST-CASES.xlsx')['테스트 케이스']; print([(r[0].value, r[9].value) for r in s.iter_rows(min_row=2)])"`로 확인해 보고서에 붙인다.

- [ ] **Step 6: Full suite and commit**

```bash
git add docs/test-cases.yaml docs/TEST-CASES.xlsx scripts/test_cases.py backend/tests/test_test_cases_doc.py backend/pyproject.toml backend/uv.lock
git commit -m "테스트 케이스 문서: 원본 YAML과 엑셀 생성·실행 결과 채우기"
```

(`pyproject.toml`·`uv.lock`이 바뀌지 않았으면 빼고 add한다.)

---

### 마무리 (컨트롤러)

- `CLAUDE.md` 실행 표에 "테스트 케이스 문서 | `uv run --directory backend python ../scripts/test_cases.py run`" 한 줄, 구조에 `backend/tests/acceptance/`(TC별 인수 테스트)·`docs/test-cases.yaml` 한 줄.
- `docs/EVALUATION.md`에 테스트 케이스 문서를 가리키는 한 줄.
- HANDOFF(기준일·main·테스트 수·지금 상태·다음 할 일), WBS 행(테스트 케이스 TC2·TC4~8 완료 #37).
- PR `task/37-test-cases`.
