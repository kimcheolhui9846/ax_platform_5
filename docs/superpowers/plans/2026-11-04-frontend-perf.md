# TC1 화면 전환 0.5ms 이하 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 버튼을 눌러 다음 화면으로 넘어갈 때의 상태 갱신(reducer)과 화면 판단(screenModel·needsLoad) 계산이 화면 전환마다 중앙값 0.5ms 이하임을 자동 테스트로 매번 재고, 테스트 케이스 문서 TC1을 자동 행으로 바꾼다.

**Architecture:** 앱 상태는 순수 reducer 하나(`frontend/src/app/state.ts`)가 바꾸고, 그릴 화면은 순수 함수 `screenModel`(`screenModel.ts`), 불러올 데이터는 `needsLoad`(`load.ts`)가 정한다. 네트워크를 뺀 "화면 전환 하나" = 이동·응답 동작을 reducer에 넣고 → 화면 모델과 불러오기를 계산하는 것. 시작 전 측정(개발 PC)에서 이 계산은 중앙값 약 0.0013ms로 기준보다 수백 배 빠르므로 코드 최적화는 하지 않고(YAGNI), 실제보다 큰 데이터(작업 200개, 정밀 모드 답 10개, 섹션 12개)로 모든 화면 전환을 재는 회귀 테스트를 둔다. 이후 누가 느린 계산을 넣으면 이 테스트가 깨진다.

**Tech Stack:** TypeScript, vitest(node 환경), `performance.now()`.

## Global Constraints

- 기준: 화면 전환 하나의 계산 시간 **중앙값 0.5ms 이하** (`LIMIT_MS = 0.5`).
- 측정 범위: 상태 갱신 + 화면 판단(reducer → screenModel + needsLoad). 네트워크·React 렌더는 제외(사용자 결정).
- 테스트 제목은 `docs/test-cases.yaml`의 `tests:`가 `frontend:src/acceptance/tc1.test.ts::<제목>`으로 그대로 가리킨다. 제목은 파일 안에서 유일해야 하고 `it("제목"` 형태(템플릿·`it.each` 금지)여야 `backend/tests/test_test_cases_doc.py`가 찾는다.
- 앱 코드(`frontend/src/app/**`, `lib/**`)는 바꾸지 않는다. 테스트 도우미는 `frontend/src/testing/`에 둔다.
- 줄바꿈 LF. 커밋 메시지에 AI 공동저자·생성 표기 금지.
- 명령: 프론트 테스트 `npm --prefix frontend test`, 빌드·타입 `npm --prefix frontend run build`, 백엔드 `uv run --directory backend pytest`.

---

### Task 1: 측정 도우미와 TC1 인수 테스트

**Files:**
- Create: `frontend/src/testing/timing.ts`
- Create: `frontend/src/testing/timing.test.ts`
- Create: `frontend/src/acceptance/tc1.test.ts`

**Interfaces:**
- Produces: `median(values: readonly number[]): number`, `medianMs(run: () => void, times?: number, warmup?: number): number` (`frontend/src/testing/timing.ts`). 테스트 제목 세 개(Task 2가 YAML에 그대로 쓴다):
  - `TC1-1 질문 흐름의 화면 전환(홈→요청→모드→질문→확인·답 고치기)은 0.5ms 이하`
  - `TC1-2 결과 흐름의 화면 전환(생성 중→결과→문구 수정·근거·저장·버전)은 0.5ms 이하`
  - `TC1-3 목록 화면 전환(작업 200개, 내 작업·결과물·홈)은 0.5ms 이하`

- [ ] **Step 1: 도우미의 실패하는 테스트**

`frontend/src/testing/timing.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { median, medianMs } from "./timing";

describe("median", () => {
  it("홀수 개면 가운데 값이다", () => {
    expect(median([3, 1, 2])).toBe(2);
  });

  it("짝수 개면 가운데 두 값의 평균이다", () => {
    expect(median([4, 1, 3, 2])).toBe(2.5);
  });

  it("받은 배열은 바꾸지 않는다", () => {
    const values = [3, 1, 2];
    median(values);
    expect(values).toEqual([3, 1, 2]);
  });

  it("값이 없으면 오류다", () => {
    expect(() => median([])).toThrow();
  });
});

describe("medianMs", () => {
  it("데우기 횟수와 잴 횟수만큼 부른다", () => {
    let calls = 0;
    medianMs(() => { calls += 1; }, 10, 3);
    expect(calls).toBe(13);
  });

  it("걸린 시간은 0 이상의 밀리초다", () => {
    expect(medianMs(() => {}, 5, 0)).toBeGreaterThanOrEqual(0);
  });
});
```

- [ ] **Step 2: 실패 확인**

Run: `npm --prefix frontend test -- src/testing/timing.test.ts`
Expected: FAIL (`./timing` 없음)

- [ ] **Step 3: 도우미 구현**

`frontend/src/testing/timing.ts`:

```ts
// 테스트에서 쓰는 계산 시간 측정. 한 번의 튀는 값(GC 등)에 흔들리지 않게 중앙값을 쓴다.

/** 값들의 중앙값(짝수 개면 가운데 두 값의 평균). 받은 배열은 바꾸지 않는다. */
export function median(values: readonly number[]): number {
  if (values.length === 0) throw new Error("중앙값을 낼 값이 없다");
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/** run을 warmup번 돌려 데운 뒤 times번 재서, 한 번 걸린 시간(ms)의 중앙값을 낸다. */
export function medianMs(run: () => void, times = 500, warmup = 50): number {
  for (let i = 0; i < warmup; i += 1) run();
  const spent: number[] = [];
  for (let i = 0; i < times; i += 1) {
    const start = performance.now();
    run();
    spent.push(performance.now() - start);
  }
  return median(spent);
}
```

- [ ] **Step 4: 통과 확인**

Run: `npm --prefix frontend test -- src/testing/timing.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 5: TC1 인수 테스트 작성**

`frontend/src/acceptance/tc1.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { needsLoad } from "../app/load";
import { screenModel } from "../app/screenModel";
import type { ScreenModel } from "../app/screenModel";
import { initialState, reducer } from "../app/state";
import type { Action, AppState } from "../app/state";
import { HOME } from "../lib/routes";
import type { Route } from "../lib/routes";
import {
  makeFlowItem,
  makeForm,
  makeQuestion,
  makeResult,
  makeSession,
  makeSessionSummary,
  makeTask,
  makeVersionView,
} from "../testing/factories";
import { medianMs } from "../testing/timing";

// TC1: 버튼을 눌러 다음 화면으로 넘어갈 때, 네트워크를 뺀 계산(상태 갱신 reducer → 화면 판단 screenModel·needsLoad)이
// 화면 전환마다 중앙값 0.5ms 이하인지 잰다. 데이터는 실제보다 크게 잡는다(작업 200개, 정밀 모드 답 10개, 섹션 12개).
const LIMIT_MS = 0.5;

const TASKS = ["business_plan", "product_planning", "branding", "marketing", "ir_pitch"].map((task_type) => makeTask({ task_type }));
const SESSIONS = Array.from({ length: 200 }, (_, i) => makeSessionSummary({ session_id: `sess_${i}` }));
const FORM = makeForm();

const FIELDS = Array.from({ length: 10 }, (_, i) => `field_${i}`);
const ROW = makeSession().summary[0];
const SUMMARY = FIELDS.map((field) => ({ ...ROW, field }));
const ANSWERED = FIELDS.map((field, i) =>
  makeFlowItem({ field, status: "answered", answer: "답", question: makeQuestion({ question_id: `q_${i}`, field }) }),
);
const NEXT = makeQuestion({ question_id: "q_next", field: "extra" });
const ASKING = makeSession({
  mode: "precise",
  next_question: NEXT,
  summary: SUMMARY,
  flow: [...ANSWERED, makeFlowItem({ field: "extra", status: "current", question: NEXT })],
});
const CONFIRMING = makeSession({ mode: "precise", next_question: null, summary: SUMMARY, flow: ANSWERED });
const DONE = { ...CONFIRMING, has_result: true };

const BASE_RESULT = makeResult();
const SECTIONS = Array.from({ length: 12 }, (_, i) => ({
  ...BASE_RESULT.result.sections[0],
  order: i + 1,
  heading: `섹션 ${i + 1}`,
  blocks: [{ type: "text" as const, text: "본문 문장. ".repeat(200) }],
}));
const RESULT = makeResult({ summary: SUMMARY, result: { ...BASE_RESULT.result, sections: SECTIONS } });
const SAVED_VERSION = makeVersionView({
  version: { ...RESULT.version, saved: true },
  result: RESULT.result,
  summary: SUMMARY,
});

const SID = ASKING.session_id;
const REQUEST: Route = { name: "request", task: "product_planning", from: null };
const MODE: Route = { name: "mode", task: "product_planning", from: null };
const QUESTION: Route = { name: "question", sessionId: SID };
const CONFIRM: Route = { name: "confirm", sessionId: SID };
const RESULT_ROUTE: Route = { name: "result", sessionId: SID };
const EVIDENCE: Route = { name: "evidence", sessionId: SID };
const SAVED: Route = { name: "saved", sessionId: SID, version: 1 };
const VERSION: Route = { name: "version", sessionId: SID, version: 1 };
const WORK: Route = { name: "work" };
const DOCUMENTS: Route = { name: "documents" };

/** 응답을 기다리는 요청(seq 1). 응답 동작은 이 요청의 것일 때만 받아들여진다. */
const WAITING = { seq: 1, load: null, generating: false };

/** route 화면에 과제 목록을 받아 둔 상태. */
function at(route: Route, data: Partial<AppState> = {}): AppState {
  return { ...initialState(route), tasks: TASKS, ...data };
}

type Transition = { name: string; from: AppState; actions: Action[]; screen: ScreenModel["kind"] };

/** 화면 전환 하나: 동작을 reducer에 넣고, 그릴 화면과 불러올 데이터를 정한다. */
function transit(t: Transition): ScreenModel["kind"] {
  const state = t.actions.reduce(reducer, t.from);
  needsLoad(state);
  return screenModel(state).kind;
}

/** 화면 전환마다 도착한 화면이 맞는지, 계산 시간 중앙값이 기준 이하인지 확인한다. */
function check(transitions: Transition[]) {
  for (const t of transitions) {
    expect(transit(t), t.name).toBe(t.screen);
    expect(medianMs(() => transit(t)), t.name).toBeLessThanOrEqual(LIMIT_MS);
  }
}

const QUESTION_FLOW: Transition[] = [
  { name: "홈 → 요청(과제 카드)", from: at(HOME, { sessions: SESSIONS, form: FORM }), actions: [{ type: "navigated", route: REQUEST }], screen: "request" },
  { name: "요청 → 모드(다음)", from: at(REQUEST, { form: FORM }), actions: [{ type: "navigated", route: MODE }], screen: "mode" },
  {
    name: "모드 → 첫 질문(세션 만들기 응답)",
    from: at(MODE, { form: FORM, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: ASKING, next: QUESTION, noticeConsumed: "product_planning", notice: null }],
    screen: "question",
  },
  {
    name: "질문 → 다음 질문(답하기 응답)",
    from: at(QUESTION, { session: ASKING, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: ASKING, next: null, noticeConsumed: null, notice: null }],
    screen: "question",
  },
  {
    name: "마지막 질문 → 확인(답하기 응답)",
    from: at(QUESTION, { session: ASKING, inflight: WAITING }),
    actions: [{ type: "sessionLoaded", seq: 1, session: CONFIRMING, next: CONFIRM, noticeConsumed: null, notice: null }],
    screen: "confirm",
  },
  {
    name: "질문 → 답 고치기(흐름 패널)",
    from: at(QUESTION, { session: ASKING }),
    actions: [{ type: "navigated", route: { name: "revise", sessionId: SID, questionId: "q_0" } }],
    screen: "revise",
  },
];

const RESULT_FLOW: Transition[] = [
  {
    name: "확인 → 생성 중(초안 만들기)",
    from: at(CONFIRM, { session: CONFIRMING }),
    actions: [{ type: "requested", seq: 1, load: null, generating: true }],
    screen: "generating",
  },
  {
    name: "생성 중 → 결과(생성 응답)",
    from: at(CONFIRM, { session: CONFIRMING, inflight: { seq: 1, load: null, generating: true } }),
    actions: [{ type: "resultLoaded", seq: 1, result: RESULT, next: RESULT_ROUTE, outdatesSession: true, notice: null }],
    screen: "result",
  },
  {
    name: "결과 → 문구 수정",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT }),
    actions: [{ type: "navigated", route: { name: "edit", sessionId: SID, order: 3 } }],
    screen: "edit",
  },
  {
    name: "결과 → 근거 검토(자료 응답)",
    from: at(EVIDENCE, { session: DONE, result: RESULT, inflight: WAITING }),
    actions: [{ type: "evidenceLoaded", seq: 1, sessionId: SID, items: [] }],
    screen: "evidence",
  },
  {
    name: "결과 → 저장 완료(저장 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT, inflight: WAITING }),
    actions: [{ type: "versionSaved", seq: 1, version: SAVED_VERSION, next: SAVED }],
    screen: "saved",
  },
  {
    name: "내 작업 → 버전 보기(버전 응답)",
    from: at(VERSION, { session: DONE, inflight: WAITING }),
    actions: [{ type: "versionLoaded", seq: 1, version: SAVED_VERSION }],
    screen: "version",
  },
];

const LIST_FLOW: Transition[] = [
  {
    name: "결과 → 내 작업(메뉴, 목록 응답)",
    from: at(RESULT_ROUTE, { session: DONE, result: RESULT, sessions: SESSIONS }),
    actions: [
      { type: "navigated", route: WORK },
      { type: "requested", seq: 1, load: "sessions", generating: false },
      { type: "sessionsLoaded", seq: 1, sessions: SESSIONS },
    ],
    screen: "work",
  },
  { name: "내 작업 → 결과물(메뉴)", from: at(WORK, { sessions: SESSIONS }), actions: [{ type: "navigated", route: DOCUMENTS }], screen: "documents" },
  { name: "결과물 → 홈(메뉴)", from: at(DOCUMENTS, { sessions: SESSIONS }), actions: [{ type: "navigated", route: HOME }], screen: "home" },
];

describe("TC1 화면 전환 계산 시간", () => {
  it("TC1-1 질문 흐름의 화면 전환(홈→요청→모드→질문→확인·답 고치기)은 0.5ms 이하", () => {
    check(QUESTION_FLOW);
  });

  it("TC1-2 결과 흐름의 화면 전환(생성 중→결과→문구 수정·근거·저장·버전)은 0.5ms 이하", () => {
    check(RESULT_FLOW);
  });

  it("TC1-3 목록 화면 전환(작업 200개, 내 작업·결과물·홈)은 0.5ms 이하", () => {
    check(LIST_FLOW);
  });
});
```

참고(코드에서 확인한 동작):
- `navigate`는 지금 폼의 `task_type`이 새 주소의 과제와 같으면 폼을 둔다(`makeForm()`의 `task_type`은 `product_planning`).
- 목록이 아닌 화면에서 목록 화면(`work`)으로 들어오면 `sessions`를 비우고 다시 받는다. 그래서 TC1-3 첫 전환은 이동 → 요청 → 목록 응답 세 동작이다.
- `resultLoaded`는 `sessionOutdated`만 세우고 세션은 그대로라 `CONFIRMING`(`has_result: false`)이면 화면은 `result`(결과 null)다. 그래도 화면 종류는 `result`다.

- [ ] **Step 6: 실행**

Run: `npm --prefix frontend test -- src/acceptance/tc1.test.ts`
Expected: PASS (3 tests). 화면 종류 단언이 실패하면 전환 데이터(시작 상태·동작)를 고친다. 기준(0.5ms)·측정 범위는 바꾸지 않는다.

느린 계산을 넣으면 실패하는지 한 번 확인한다(커밋하지 않는다): `screenModel`의 `resolve` 첫 줄에 `for (let i = 0; i < 3e6; i += 1);`을 잠깐 넣고 위 명령이 FAIL인지 본 뒤 되돌린다.

- [ ] **Step 7: 전체 프론트 테스트와 빌드**

Run: `npm --prefix frontend test` → 전부 PASS
Run: `npm --prefix frontend run build` → 타입 오류 없음

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/testing/timing.ts frontend/src/testing/timing.test.ts frontend/src/acceptance/tc1.test.ts
git commit -m "TC1 화면 전환 계산 시간 인수 테스트(중앙값 0.5ms 이하)"
```

---

### Task 2: 테스트 케이스 문서·WBS·HANDOFF

**Files:**
- Modify: `docs/test-cases.yaml` (TC1-1 `예정` 행 → TC1-1~TC1-3 `자동` 행)
- Modify: `docs/TEST-CASES.xlsx` (스크립트로 다시 만든다)
- Modify: `docs/WBS.xlsx` (스크립트로)
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: Task 1의 테스트 제목 세 개(위 Interfaces 그대로).

- [ ] **Step 1: YAML의 TC1-1 행(`- id: TC1-1`부터 `note: 'PR #38에서 자동 테스트로 바꾼다'`까지)을 아래 세 행으로 바꾼다**

```yaml
- id: TC1-1
  group: TC1
  item: 프론트엔드 수정 후 최적화(리액트 반응 속도 0.5ms 이하)
  title: 질문 흐름의 화면 전환(홈→요청→모드→질문→확인·답 고치기)은 0.5ms 이하
  precondition: 화면 상태·응답 데이터는 미리 준비(네트워크·렌더 제외), 과제 5개·작업 200개·정밀 모드 답 10개
  steps:
  - 화면마다 이동 버튼에 해당하는 동작(이동·응답)을 reducer에 넣고 화면 모델·불러오기를 계산한다
  - 데운 뒤 500번 재서 중앙값을 낸다
  expected: 전환마다 도착 화면이 맞고, 계산 시간 중앙값 0.5ms 이하
  method: 자동
  tests:
  - frontend:src/acceptance/tc1.test.ts::TC1-1 질문 흐름의 화면 전환(홈→요청→모드→질문→확인·답 고치기)은 0.5ms 이하
- id: TC1-2
  group: TC1
  item: 프론트엔드 수정 후 최적화(리액트 반응 속도 0.5ms 이하)
  title: 결과 흐름의 화면 전환(생성 중→결과→문구 수정·근거·저장·버전)은 0.5ms 이하
  precondition: 결과 섹션 12개, 기준 10개
  steps:
  - 생성 시작·생성 응답·문구 수정 이동·근거 응답·저장 응답·버전 응답을 reducer에 넣고 화면 모델·불러오기를 계산한다
  - 데운 뒤 500번 재서 중앙값을 낸다
  expected: 전환마다 도착 화면이 맞고, 계산 시간 중앙값 0.5ms 이하
  method: 자동
  tests:
  - frontend:src/acceptance/tc1.test.ts::TC1-2 결과 흐름의 화면 전환(생성 중→결과→문구 수정·근거·저장·버전)은 0.5ms 이하
- id: TC1-3
  group: TC1
  item: 프론트엔드 수정 후 최적화(리액트 반응 속도 0.5ms 이하)
  title: 목록 화면 전환(작업 200개, 내 작업·결과물·홈)은 0.5ms 이하
  precondition: 내 작업 200개
  steps:
  - 결과 → 내 작업(이동·목록 요청·목록 응답), 내 작업 → 결과물, 결과물 → 홈을 reducer에 넣고 화면 모델·불러오기를 계산한다
  - 데운 뒤 500번 재서 중앙값을 낸다
  expected: 전환마다 도착 화면이 맞고, 계산 시간 중앙값 0.5ms 이하
  method: 자동
  tests:
  - frontend:src/acceptance/tc1.test.ts::TC1-3 목록 화면 전환(작업 200개, 내 작업·결과물·홈)은 0.5ms 이하
```

- [ ] **Step 2: 문서 검사 테스트**

Run: `uv run --directory backend pytest tests/test_test_cases_doc.py`
Expected: 참조 위치는 통과, 엑셀 행 ID 검사는 아직 실패(TC1-2·TC1-3이 엑셀에 없음)

- [ ] **Step 3: 엑셀 다시 만들기(자동 테스트 실행 포함)**

Run: `uv run --directory backend python ../scripts/test_cases.py run`
Expected: 종료 코드 0, `docs/TEST-CASES.xlsx` 갱신. 다시 `uv run --directory backend pytest` → 전부 PASS.

- [ ] **Step 4: WBS**

```bash
uv run --no-project --with openpyxl python scripts/wbs.py list   # 6.13의 열 이름·명령 형식 확인
```
6.13을 상태 `완료`, 완료일 2026-11-04, 진척률 1, 비고 `PR #38`로, 기준일을 2026-11-04로 (`scripts/wbs.py set`·`date`, 사용법은 `--help`). 출력이 깨지면 `PYTHONIOENCODING=utf-8`.

- [ ] **Step 5: HANDOFF**

`docs/HANDOFF.md`:
- 머리: `main: \`fe92f2f\` (PR #37까지 머지)`, 테스트 수는 `uv run --directory backend pytest`·`npm --prefix frontend test`의 실제 숫자.
- "지금 상태" 표 마지막(#37 행 아래)에 행 추가: `| 화면 전환 계산 시간(TC1) | #38 | 버튼 → 다음 화면의 상태 갱신·화면 판단(reducer → screenModel·needsLoad, 네트워크·렌더 제외)을 화면 전환 15개마다 중앙값으로 재는 인수 테스트 \`frontend/src/acceptance/tc1.test.ts\`(기준 0.5ms, 측정 도우미 \`testing/timing.ts\`). 시작 전 측정 약 0.001ms라 코드 최적화는 하지 않았다 |`
- "다음 할 일"에서 TC1(#38) 항목을 지우고 남은 TC3(#39)·수동 TC8-7은 그대로 둔다.

- [ ] **Step 6: 커밋**

```bash
git add docs/test-cases.yaml docs/TEST-CASES.xlsx docs/WBS.xlsx docs/HANDOFF.md
git commit -m "TC1 테스트 케이스 문서·WBS·인수인계 갱신"
```
