# 디자인 피드백 반영(생성 중·생성 실패·최신 아님·이미지 상자·모드 문구) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 디자이너가 보낸 수정본(`design/2026-10-17-ux-v2-feedback/`)의 바뀐 화면을 React에 반영한다: 생성 중 화면, 생성 실패 화면, 결과가 최신이 아님 배너(저장·내려받기 막기), 결과 문서의 이미지 상자 모양과 위치(첫 섹션), 질문 수를 뺀 모드 설명.

**Architecture:** 생성 중은 "지금 기다리는 요청이 생성이다"를 요청 기록(`Inflight.generating`)에 담아 화면 모델이 고른다(주소는 그대로). 생성 실패는 새 주소 `#/s/{id}/failed`로, 생성 요청이 실패하면 리듀서가 그 주소로 옮긴다. 최신 아님 배너와 버튼 막기는 결과 화면의 순수 판단(`lib/actions.ts`)으로 정한다. API는 바뀌지 않는다(백엔드는 이미지 대표 섹션 한 줄만).

**Tech Stack:** React 19·Vite·TypeScript·vitest(프론트), FastAPI(백엔드 한 곳).

## Global Constraints

- 디자인 원본: `design/2026-10-17-ux-v2-feedback/index.html`(받은 그대로, 고치지 않는다). 직전 원본 `design/2026-10-16-ux-v2/`와의 차이만 반영한다. 주요 함수: `generatingView`, `failedView`, `staleBanner`, `imageBlock`, `MODES`.
- 커밋 메시지·PR 본문에 AI 공동저자·생성 표기를 넣지 않는다. git 신원 `kim cheol hui <144594976+kimcheolhui9846@users.noreply.github.com>`. `backend/.env`는 출력하거나 고치지 않는다.
- 프론트: 상태는 `app/state.ts`의 `reducer`(순수)만 바꾼다. 화면·컴포넌트는 props만 받는다. 판단은 `lib/`·`app/`의 순수 함수와 테스트. 색·글자 크기·폭·선·모서리는 `var(--…)`만(`tokens.test.ts`). 미리보기 프레임에 스크롤 상자를 두지 않는다. jsdom은 없고 패키지를 늘리지 않는다(렌더 테스트는 `renderToString`).
- 명령: 백엔드 `uv run --directory backend pytest -q`, 프론트 `npm --prefix frontend test`, 빌드 `npm --prefix frontend run build`.

## 결정 사항 (컨트롤러)

1. **'생성 취소'는 넣지 않는다.** 생성은 서버가 끝까지 처리하는 요청이라 화면에서 취소해도 새 버전이 생긴다. 디자인의 "취소해도 이전 결과가 유지돼요"와 실제가 어긋난다.
2. **안내 페이지의 상태 시연 버튼(`demo-*`)은 넣지 않는다.** 같은 상태는 `/preview` 갤러리 프레임이 보여 준다.
3. **흐름 패널의 진행 표시("질문 2/5")는 그대로 둔다**(설계 결정 2: 진행 수를 보여 준다). 디자인의 "예시 질문 진행"은 프로토타입 문구다.
4. **'다른 예시 보기'·'현재 정보로 초안 만들기'는 이미 모든 질문에 있다.** 할 일 없음.
5. **생성 실패 화면의 문구는 고정이다**(디자인 `failedView` 기본 문구). 구체 사유(서버 문구)는 지금처럼 알림(토스트)으로 나간다. 실패 주소는 직접 열어도 같은 화면이고 '다시 시도하기'는 그대로 생성이다.
6. **최신이 아닌 결과는 저장·내려받기를 막는다**(디자인과 같다). 버전 보기 화면의 내려받기는 지난 버전을 받는 기능이라 막지 않는다.
7. **이미지는 첫 섹션 끝**에 둔다(디자인 `r.sections.map((s,i)=>…+(i===0?imageBlock():''))`). 백엔드 `image_target`을 첫 섹션(가장 작은 order)으로 바꾼다.

---

### Task 1: 모드 설명·이미지 상자 모양·첫 섹션 이미지

**Files:**
- Modify: `backend/app/core/results.py`(`image_target`), `backend/tests/test_images.py`
- Modify: `frontend/src/lib/modes.ts`, `frontend/src/screens/ModeScreen.tsx`
- Modify: `frontend/src/components/ResultDocument.tsx`, `frontend/src/styles/screens.css`, `frontend/src/styles/tokens.css`
- Modify: `frontend/src/preview/fixtures.ts`(`RESULT_IMAGE`를 첫 섹션으로)
- Test: `frontend/src/components/components.test.tsx`, `frontend/src/lib/modes.test.ts`(없으면 만든다)
- Modify: `CLAUDE.md`(이미지 대표 섹션 문장)

**Interfaces:**
- Produces: `image_target(sections) -> ResultSection | None`(가장 작은 order 섹션); `MODE_COPY[mode].detail: string`(함수가 아니다).

- [ ] **Step 1: 백엔드 실패 테스트** — `backend/tests/test_images.py`의 `test_image_target_prefers_the_first_suggestion`을 바꾼다:

```python
def test_image_target_is_the_first_section():
    assert image_target([section(2, CardType.SUGGESTION), section(1, CardType.DIAGNOSIS)]).order == 1
    assert image_target([section(1, CardType.ACTION)]).order == 1
    assert image_target([]) is None
```

Run: `uv run --directory backend pytest tests/test_images.py -q` → FAIL.

- [ ] **Step 2: 구현** — `backend/app/core/results.py`:

```python
def image_target(sections: Sequence[ResultSection]) -> ResultSection | None:
    """[순수] 이미지를 붙일 대표 섹션: 첫 섹션(가장 앞 order, 디자인의 이미지 자리). 섹션이 없으면 None."""
    return min(sections, key=lambda s: s.order, default=None)
```

`CardType`를 이 함수에서만 쓰고 있었다면 import는 그대로 둔다(다른 곳에서 쓴다). `CLAUDE.md` 하네스 원칙의 이미지 문장 "대표 섹션(첫 제안 섹션, 없으면 첫 섹션)"을 "첫 섹션"으로 고친다. Run → PASS(전체 `uv run --directory backend pytest -q`).

- [ ] **Step 3: 모드 문구 실패 테스트** — `frontend/src/lib/modes.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { MODE_COPY } from "./modes";

describe("모드 문구", () => {
  it("질문 수를 쓰지 않는다(상한은 진행 표시가 알린다)", () => {
    expect(MODE_COPY.quick.detail).toBe("꼭 필요한 질문으로 방향을 잡고, 주요 기준을 확인해 초안을 만들어요.");
    expect(MODE_COPY.standard.detail).toBe("질문을 주고받으며 아이디어와 실행 기준을 차근차근 구체화해요.");
    expect(MODE_COPY.precise.detail).toBe("배경과 세부 조건을 살펴보며, 제약과 판단 근거까지 확인해요.");
    for (const copy of Object.values(MODE_COPY)) expect(copy.detail).not.toMatch(/\d/);
  });
});
```

- [ ] **Step 4: 구현** — `lib/modes.ts`: `type ModeCopy = { name: string; headline: string; detail: string }`, 위 세 문장을 `detail`에, 파일 주석을 "모드 카드 문구(디자인 수정본). 질문 수는 쓰지 않는다(상한은 질문 화면의 진행 표시가 알린다)."로. `ModeScreen.tsx`: `{copy.detail}`로 바꾸고 `question_cap`을 쓰지 않으면 구조 분해에서 뺀다(`form.modes.map(({ mode }) => …)`). Run → PASS.

- [ ] **Step 5: 이미지 상자 실패 테스트** — `components.test.tsx`의 "불러온 이미지는 대체 글과 설명을 달아 그린다"를 디자인 구조로 바꾼다:

```tsx
  it("이미지 상자는 왼쪽 이미지, 오른쪽 제목(대체 글)과 설명이다", () => {
    const html = renderToString(<ResultDocument {...documentContent(makeTask(), shown, false, { a: "data:image/svg+xml;base64,AA" })} />);
    expect(html).toContain('<figure class="document-image">');
    expect(html).toContain('<div class="image-slot"><img src="data:image/svg+xml;base64,AA" alt="제작 방향 참고 이미지"/></div>');
    expect(html).toContain("<figcaption><h3>제작 방향 참고 이미지</h3><p>AI 참고 이미지</p></figcaption>");
  });

  it("아직 못 불러온 이미지는 자리 상자에 대체 글을 둔다", () => {
    const html = renderToString(<ResultDocument {...documentContent(makeTask(), shown, false, {})} />);
    expect(html).not.toContain("<img");
    expect(html).toContain('<div class="image-slot" role="img" aria-label="제작 방향 참고 이미지"><span class="image-symbol" aria-hidden="true">▧</span>');
  });
```

(기존 "아직 못 불러온 이미지" 테스트를 위 것으로 바꾼다.)

- [ ] **Step 6: 구현** — `ResultDocument.tsx`의 이미지 분기:

```tsx
          <figure key={block.key} className="document-image">
            {block.src !== null ? (
              <div className="image-slot">
                <img src={block.src} alt={block.alt} />
              </div>
            ) : (
              <div className="image-slot" role="img" aria-label={block.alt}>
                <span className="image-symbol" aria-hidden="true">
                  ▧
                </span>
                <span className="small muted">이미지를 불러오는 중이거나 불러오지 못했어요</span>
              </div>
            )}
            <figcaption>
              <h3>{block.alt}</h3>
              {block.caption && <p>{block.caption}</p>}
            </figcaption>
          </figure>
```

(`renderToString`이 JSX 줄바꿈을 공백 없이 붙이므로 기대 문자열과 맞는지 실행해 확인하고, 다르면 테스트가 아니라 JSX 공백을 맞춘다.)

`screens.css`의 `.doc-figure…` 세 규칙을 디자인 값으로 바꾼다(토큰만):

```css
.document-image {
  display: grid; grid-template-columns: minmax(var(--image-slot-min), var(--image-slot-max)) minmax(0, 1fr);
  gap: var(--space-6); align-items: center; margin: var(--space-1) 0 var(--space-2); padding: var(--space-4);
  border: var(--line-width) solid var(--color-line); border-radius: var(--radius-md); background: var(--color-surface);
}
.image-slot {
  aspect-ratio: 16 / 9; min-width: 0; overflow: hidden;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--space-1);
  background: var(--color-soft); border: var(--line-width) dashed var(--color-muted); border-radius: var(--radius-sm);
}
.image-slot img { display: block; width: 100%; height: 100%; object-fit: cover; }
.image-symbol { font-size: var(--text-image-symbol); color: var(--color-muted); line-height: 1; }
.document-image figcaption { display: flex; flex-direction: column; gap: var(--space-2); font-size: var(--text-note); line-height: var(--text-sm-line); }
.document-image h3 { font-size: var(--text-sm); line-height: var(--text-sm-line); }
```

`@container app (max-width: 719px)` 블록에 `.document-image { grid-template-columns: 1fr; gap: var(--space-4); padding: var(--space-3); }`. `tokens.css`에서 `--figure-placeholder-height`를 지우고(더 쓰지 않으면) `--image-slot-min: 160px; --image-slot-max: 280px;`와 글자 크기 묶음에 `--text-image-symbol: 28px;`를 더한다. 흰 표면 토큰 이름은 `tokens.css`에서 확인한다(카드 배경에 쓰는 토큰, 없으면 `.card` 규칙이 쓰는 값).

`preview/fixtures.ts`의 `RESULT_IMAGE`는 `s.order === 1` 섹션 끝에 이미지를 붙이고, alt를 "상품 콘셉트 참고 이미지"로.

- [ ] **Step 7: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build` → PASS.

- [ ] **Step 8: 커밋**

```bash
git add backend frontend CLAUDE.md
git commit -m "디자인 피드백: 모드 설명에서 질문 수 빼기, 결과 이미지는 첫 섹션에 이미지 상자로"
```

---

### Task 2: 생성 중 화면

**Files:**
- Modify: `frontend/src/app/state.ts`, `frontend/src/app/requests.ts`, `frontend/src/app/handlers.ts`, `frontend/src/app/screenModel.ts`, `frontend/src/app/view.tsx`
- Create: `frontend/src/screens/GenerationScreens.tsx`
- Modify: `frontend/src/styles/screens.css`, `frontend/src/styles/tokens.css`
- Modify: `frontend/src/preview/frames.tsx`, `frontend/src/preview/frames.test.tsx`
- Test: `app/state.test.ts`, `app/requests.test.ts`, `app/handlers.test.ts`, `app/screenModel.test.ts`, `components/components.test.tsx`(또는 `app/view.test.tsx`)

**Interfaces:**
- Produces:
  - `Inflight = { seq: number; load: string | null; generating: boolean }`; 동작 `requested`에 `generating: boolean`
  - `Call<T>.generating: boolean`(생성 요청이면 true. 이 값은 동작을 바꾸는 플래그가 아니라 요청 기록에 남기는 사실이다)
  - `ScreenModel`에 `{ kind: "generating"; task: TaskSummary; session: SessionView }`
  - `GeneratingMain()`, `GeneratingSide({ flow })` (`screens/GenerationScreens.tsx`)

- [ ] **Step 1: 실패 테스트**
  - `state.test.ts`: `requested`가 `generating`을 `inflight`에 남긴다(`{ type: "requested", seq: 1, load: null, generating: true }` → `inflight.generating === true`).
  - `requests.test.ts`: `createRunner`가 `call.generating`을 `requested`에 싣는다.
  - `handlers.test.ts`: `generate`·`applySupplements`의 `run` 호출은 `generating: true`, 그 밖의 요청(답변·저장·문구 수정·근거 반영·보완 저장)과 `startLoad`의 불러오기는 `generating: false`.
  - `screenModel.test.ts`: 세션이 있는 세션 화면(확인·결과·문구 수정 등)에서 `inflight.generating`이면 `{ kind: "generating", task, session }`. 세션을 아직 못 받았으면 loading 그대로. 과제·목록 화면에는 영향이 없다.
  - `components.test.tsx`: `GeneratingMain`이 `aria-busy="true"`, "초안 생성 중", "답변을 바탕으로 초안을 정리하고 있어요", `role="status"` 문장, 그리고 "생성 취소" 버튼이 없음; `GeneratingSide`가 "정리할 기준"과 흐름 요약을 그린다.

- [ ] **Step 2: 실패 확인** — `npm --prefix frontend test` → FAIL

- [ ] **Step 3: 구현**
  - `state.ts`: `Inflight`·`requested`에 `generating` 추가, `reducer`의 `requested` 분기가 `inflight: { seq, load, generating }`.
  - `requests.ts`: `Call<T>`에 `generating: boolean; // 초안 생성 요청이면 true(생성 중 화면)`. `createRunner`가 `dispatch({ type: "requested", seq: mine, load, generating })`. `startLoad`의 모든 불러오기는 `generating: false`.
  - `handlers.ts`: `generateWith`의 `run`만 `generating: true`, 나머지 `run` 호출은 `generating: false`.
  - `screenModel.ts`: `resolve`의 세션 분기에서 `task`를 찾은 직후(버전·결과 분기보다 먼저):

```ts
      // 초안을 만드는 동안은 어느 세션 화면이든 생성 중 화면이다(주소는 그대로)
      if (state.inflight?.generating) return { kind: "generating", task, session };
```

  - `screens/GenerationScreens.tsx`:

```tsx
import type { FlowItem } from "../api/types";
import { FlowSummary } from "../components/FlowSummary";

/** 초안 생성 중. 서버가 끝까지 처리하는 요청이라 취소 버튼은 두지 않는다. */
export function GeneratingMain() {
  return (
    <section className="card generation-card stack" aria-busy="true">
      <div className="spinner" aria-hidden="true" />
      <p className="small">초안 생성 중</p>
      <h1>답변을 바탕으로 초안을 정리하고 있어요</h1>
      <p className="muted" role="status">
        선택한 기준과 보완 정보를 확인하고 있어요. 잠시만 기다려 주세요.
      </p>
      <div className="skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <p className="small muted">입력 내용과 이전 결과는 그대로 유지돼요.</p>
    </section>
  );
}

export function GeneratingSide({ flow }: { flow: FlowItem[] }) {
  return (
    <section className="card side-card stack" aria-label="정리할 기준">
      <h2>정리할 기준</h2>
      <FlowSummary flow={flow} />
    </section>
  );
}
```

  - `view.tsx`의 `renderScreen`: `case "generating": return { main: <GeneratingMain />, side: <GeneratingSide flow={model.session.flow} /> };`
  - `screens.css`(토큰만):

```css
/* 생성 중·생성 실패 */
.generation-card { padding: var(--space-12) var(--space-8); align-items: flex-start; gap: var(--space-6); }
.generation-card h1 { font-size: var(--text-2xl); line-height: var(--text-2xl-line); }
.spinner {
  width: var(--spinner-size); height: var(--spinner-size); border-radius: var(--radius-pill);
  border: var(--spinner-line) solid var(--color-line); border-top-color: var(--color-accent);
  animation: spin 1s linear infinite;
}
.skeleton { width: 100%; display: flex; flex-direction: column; gap: var(--space-3); }
.skeleton span { height: var(--skeleton-line); border-radius: var(--radius-sm); background: var(--color-soft); }
.skeleton span:nth-child(2) { width: 84%; }
.skeleton span:nth-child(3) { width: 64%; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation: none; } }
```

  모바일(`@container app (max-width: 719px)`)에 `.generation-card { padding: var(--space-6) var(--space-5); } .generation-card h1 { font-size: var(--text-xl); line-height: var(--text-xl-line); }`. `tokens.css`에 `--spinner-size: 36px; --spinner-line: 3px; --skeleton-line: 18px;`. 공간 토큰(`--space-12` 등)이 없으면 있는 값 중 가장 가까운 것을 쓴다.
  - `preview/frames.tsx`: `confirm-generating` 프레임을 `frame("generating", "초안 생성 중", confirm, { kind: "generating", task: PRODUCT, session: SESSION_READY }, true)`로 바꾼다. `frames.test.tsx`의 목록·`DESIGN_SCREENS`(`"generating"` 추가)를 맞춘다.

- [ ] **Step 4: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend
git commit -m "디자인 피드백: 초안 생성 중 화면(요청 기록의 generating으로 고른다)"
```

---

### Task 3: 생성 실패 화면

**Files:**
- Modify: `frontend/src/lib/routes.ts`, `frontend/src/lib/shell.ts`, `frontend/src/app/state.ts`, `frontend/src/app/requests.ts`, `frontend/src/app/handlers.ts`, `frontend/src/app/load.ts`(필요하면), `frontend/src/app/screenModel.ts`, `frontend/src/app/view.tsx`
- Modify: `frontend/src/screens/GenerationScreens.tsx`, `frontend/src/screens/ConfirmScreen.tsx`
- Modify: `frontend/src/preview/frames.tsx`, `frontend/src/preview/frames.test.tsx`
- Test: `lib/routes.test.ts`, `lib/shell.test.ts`, `app/state.test.ts`, `app/requests.test.ts`, `app/handlers.test.ts`, `app/screenModel.test.ts`, `components/components.test.tsx`
- Modify: `CLAUDE.md`(주소 목록)

**Interfaces:**
- Consumes: Task 2의 `Call.generating`, `GenerationScreens.tsx`.
- Produces:
  - 주소 `{ name: "failed"; sessionId }` ↔ `#/s/{id}/failed`
  - `Call<T>.failedRoute: Route | null`(실패했을 때 옮길 주소). 동작 `failed`에 `next: Route | null`
  - `ScreenModel`에 `{ kind: "failed"; task; session }`
  - `FailedMain({ hasResult, busy, canGenerate, onRetry, onConfirm, onShowResult })`, `FailedSide({ flow })`

- [ ] **Step 1: 실패 테스트**
  - `routes.test.ts`: `parseRoute("#/s/sess_1/failed")` ↔ `toHash`, `contextOf`는 `session:sess_1`.
  - `shell.test.ts`: `routePhase`·`railActive`가 `failed`를 `confirm`과 같이 다룬다.
  - `state.test.ts`: 기다리던 seq의 `failed`가 `next`가 있으면 `route`를 그 주소로, 알림(`toast`)은 지금처럼 메시지로 둔다; `next: null`이면 주소는 그대로.
  - `requests.test.ts`: 실패 응답과 연결 예외 모두 `failed`에 `next: call.failedRoute`를 싣는다.
  - `handlers.test.ts`: `generate`·`applySupplements`의 `failedRoute`는 `{ name: "failed", sessionId }`, 다른 요청은 `null`.
  - `screenModel.test.ts`: `failed` 주소는 세션이 있으면 `{ kind: "failed", task, session }`(세션 상태와 상관없이). 생성 중이면 생성 중이 먼저다.
  - `components.test.tsx`: `FailedMain`이 "초안 생성 실패", "초안을 만들지 못했어요", `role="alert"` 문장 "생성을 완료하지 못했어요. 입력한 내용은 유지되어 있으니 다시 시도해 주세요.", "다시 시도하기"(primary), "입력 내용 확인", 결과가 있을 때만 "이전 결과 보기", "입력 내용과 저장한 결과는 삭제되지 않았어요."; `canGenerate`가 false거나 busy면 다시 시도하기가 막힌다. `FailedSide`는 "유지된 답변"과 흐름 요약.
  - `ConfirmScreen`: 오류 문단(`session.error`)은 그대로 둔다(실패 화면을 떠나 확인으로 와도 상태를 알 수 있게).

- [ ] **Step 2: 실패 확인** — `npm --prefix frontend test` → FAIL

- [ ] **Step 3: 구현**
  - `routes.ts`: `Route`에 `| { name: "failed"; sessionId: string }`, `sessionView`에 `case "failed": return { name: "failed", sessionId };`.
  - `shell.ts`: 두 switch에서 `case "confirm":` 옆에 `case "failed":`.
  - `state.ts`: `failed` 동작에 `next: Route | null`. `settle`의 `failed`: `route: action.next ?? done.route`를 더한다(나머지 그대로).
  - `requests.ts`: `Call<T>`에 `failedRoute: Route | null; // 실패하면 옮길 주소(생성 실패 화면)`. 실패 두 곳이 `next: failedRoute`. `startLoad`는 모두 `failedRoute: null`.
  - `handlers.ts`: `generateWith`에 `failedRoute: { name: "failed", sessionId }`, 나머지 `run`은 `failedRoute: null`. `retryGeneration`은 따로 만들지 않고 실패 화면의 다시 시도하기가 `on.generate`를 부른다.
  - `load.ts`: `failed` 주소는 세션만 있으면 된다(기존 규칙이 세션을 부르므로 바뀔 것이 없는지 테스트로 확인).
  - `screenModel.ts`: 세션 분기에서 생성 중 검사 다음에 `if (route.name === "failed") return { kind: "failed", task, session };`.
  - `GenerationScreens.tsx`에:

```tsx
type FailedProps = {
  hasResult: boolean;
  busy: boolean;
  canGenerate: boolean;
  onRetry: () => void;
  onConfirm: () => void;
  onShowResult: () => void;
};

/** 초안 생성 실패. 구체 사유는 알림으로 나가고, 여기서는 입력이 남아 있음을 알리고 다시 시도하게 한다. */
export function FailedMain({ hasResult, busy, canGenerate, onRetry, onConfirm, onShowResult }: FailedProps) {
  return (
    <section className="card generation-card stack">
      <p className="small">초안 생성 실패</p>
      <h1>초안을 만들지 못했어요</h1>
      <p className="muted" role="alert">
        생성을 완료하지 못했어요. 입력한 내용은 유지되어 있으니 다시 시도해 주세요.
      </p>
      <div className="state-actions">
        <button type="button" className="btn primary" disabled={busy || !canGenerate} onClick={onRetry}>
          다시 시도하기
        </button>
        <button type="button" className="btn" disabled={busy} onClick={onConfirm}>
          입력 내용 확인
        </button>
        {hasResult && (
          <button type="button" className="btn" disabled={busy} onClick={onShowResult}>
            이전 결과 보기
          </button>
        )}
      </div>
      <p className="small muted">입력 내용과 저장한 결과는 삭제되지 않았어요.</p>
    </section>
  );
}

export function FailedSide({ flow }: { flow: FlowItem[] }) {
  return (
    <section className="card side-card stack" aria-label="유지된 답변">
      <h2>유지된 답변</h2>
      <FlowSummary flow={flow} />
    </section>
  );
}
```

  - `view.tsx`: `case "failed": return { main: <FailedMain hasResult={model.session.has_result} busy={busy} canGenerate={model.session.can_generate} onRetry={on.generate} onConfirm={on.confirm} onShowResult={on.showResult} />, side: <FailedSide flow={model.session.flow} /> };`
  - `screens.css`: `.state-actions { display: flex; flex-wrap: wrap; gap: var(--space-3); }`, 모바일에 `.state-actions { flex-direction: column; align-items: stretch; }`.
  - `preview/frames.tsx`: `confirm-failed`를 `frame("failed", "초안 생성 실패", { name: "failed", sessionId: SESSION_ID }, { kind: "failed", task: PRODUCT, session: SESSION_FAILED })`로 바꾸고, 이전 결과가 있는 실패 `frame("failed-with-result", "생성 실패 · 이전 결과 있음", …, { kind: "failed", task: PRODUCT, session: { ...SESSION_FAILED, has_result: true } })`를 더한다. `frames.test.tsx` 목록·`DESIGN_SCREENS`(`"failed"`)를 맞춘다.
  - `CLAUDE.md`의 주소 목록에 `` `#/s/{id}/failed`(생성 실패) ``, `app/` 설명에 "생성 요청(`Call.generating`)이 기다리는 동안은 세션 화면 대신 생성 중 화면, 생성이 실패하면 `failedRoute`로 실패 화면"을 한 문장.

- [ ] **Step 4: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend CLAUDE.md
git commit -m "디자인 피드백: 초안 생성 실패 화면(#/s/{id}/failed, 다시 시도·입력 확인·이전 결과)"
```

---

### Task 4: 결과가 최신이 아님 배너, 저장·내려받기 막기

**Files:**
- Modify: `frontend/src/lib/actions.ts`, `frontend/src/screens/ResultScreen.tsx`, `frontend/src/app/view.tsx`, `frontend/src/styles/screens.css`
- Test: `lib/actions.test.ts`, `components/components.test.tsx` 또는 `app/view.test.tsx`

**Interfaces:**
- Produces: `STALE_BANNER = { title: "결과가 최신이 아니에요", text: "답변이나 보완 정보가 바뀌었어요. 아래에는 바뀌기 전 결과가 그대로 있어요.", action: "바뀐 내용으로 다시 만들기" }`; `saveButton(version, stale, withSources)`가 최신이 아니면 막는다(`done: true`가 아니라 새 값 `disabled: boolean`); `STALE_SAVE_HINT = "바뀐 기준으로 결과를 먼저 다시 만들어 주세요."`; `StaleBanner({ busy, canGenerate, onRegenerate })`

- [ ] **Step 1: 실패 테스트**
  - `actions.test.ts`: `saveButton({ saved: false }, true, false)` → `{ label: "현재 버전 저장", primary: false, disabled: true }`; 최신이면 `disabled: false`, 저장했으면 `{ label: "저장한 버전이에요", primary: false, disabled: true }`(기존 `done` 자리를 `disabled`로 바꾼다).
  - 렌더 테스트: 최신이 아닌 결과 화면(`session.result_stale: true`)의 본문 위에 `role="status"` 배너(제목·문장·"바뀐 내용으로 다시 만들기" primary)가 있고, 오른쪽 패널의 저장·'문서 내려받기'가 막혀 있으며 막힌 이유(`STALE_SAVE_HINT`)가 보인다. 오른쪽 패널에 예전 `STALE_NOTICE` 문단은 없다(배너가 대신한다). 최신이면 배너가 없고 두 버튼이 열려 있다.

- [ ] **Step 2: 실패 확인** — FAIL

- [ ] **Step 3: 구현**
  - `lib/actions.ts`: `saveButton`의 반환 `done`을 `disabled`로 바꾸고 `if (stale) return { label, primary: false, disabled: true }` 분기를 저장 표시 다음에 둔다. `STALE_BANNER`·`STALE_SAVE_HINT` 상수. `STALE_NOTICE`는 답변 확인 화면이 계속 쓰므로 둔다. `saveButton`을 쓰는 곳(`ResultScreen`)을 `disabled`로 맞춘다.
  - `ResultScreen.tsx`에 배너 컴포넌트와 쓰임:

```tsx
type BannerProps = { busy: boolean; canGenerate: boolean; onRegenerate: () => void };

/** 결과가 최신이 아님(답·보완 정보가 바뀜). 아래 문서는 바뀌기 전 결과다. */
export function StaleBanner({ busy, canGenerate, onRegenerate }: BannerProps) {
  return (
    <section className="stale-banner" role="status">
      <div className="stack8">
        <h2>{STALE_BANNER.title}</h2>
        <p>{STALE_BANNER.text}</p>
      </div>
      <button type="button" className="btn primary" disabled={busy || !canGenerate} onClick={onRegenerate}>
        {STALE_BANNER.action}
      </button>
    </section>
  );
}
```

  `ResultMain`에 `onRegenerate: () => void` prop을 더하고, 결과가 있고 `session.result_stale`이면 `<div className="stack">{배너}{문서}</div>`로 그린다. `ResultSide`: `STALE_NOTICE` 문단을 지우고, 저장 버튼 `disabled={busy || save.disabled}`, 내려받기 `disabled={busy || session.result_stale}`, 그리고 `session.result_stale`일 때 버튼 묶음 아래 `<p className="small muted">{STALE_SAVE_HINT}</p>`.
  - `view.tsx`: `ResultMain`에 `onRegenerate={on.generate}`.
  - `screens.css`(토큰만):

```css
.stale-banner {
  display: flex; align-items: center; justify-content: space-between; gap: var(--space-5);
  padding: var(--space-5) var(--space-6); border: var(--line-width-strong) solid var(--color-accent);
  border-radius: var(--radius-md); background: var(--color-surface);
}
.stale-banner h2 { font-size: var(--text-lg); line-height: var(--text-lg-line); }
.stale-banner p { font-size: var(--text-sm); }
```

  `@container app (max-width: 1099px)`에 `.stale-banner { flex-direction: column; align-items: stretch; }`, 모바일에 `.stale-banner { padding: var(--space-4); }`. 굵은 선·흰 표면 토큰 이름은 `tokens.css`에서 확인한다(버튼 테두리 1.5px 토큰이 있으면 그것).
  - 미리보기의 `result-stale` 프레임이 배너를 보여 주는지 확인(모델은 그대로).

- [ ] **Step 4: 통과 확인** — `npm --prefix frontend test`, `npm --prefix frontend run build` → PASS

- [ ] **Step 5: 커밋**

```bash
git add frontend
git commit -m "디자인 피드백: 결과가 최신이 아님 배너, 낡은 결과는 저장·내려받기 막기"
```

## 브라우저 확인 (컨트롤러)

임시 SQLite DB로: 모드 화면 문구(숫자 없음) → 결과 만들기 중 생성 중 화면(스피너·뼈대, 취소 없음) → 결과 → 답 고치기 → 결과에 배너, 저장·내려받기 막힘 → 배너의 다시 만들기 → 최신. 생성 실패는 Mock 실패를 낼 수 없으므로 `/preview`의 `failed` 프레임과 렌더 테스트로 확인. 브랜딩 결과에서 첫 섹션 아래 이미지 상자(왼쪽 이미지·오른쪽 제목/설명), 390px에서 한 열. 갤러리 새 프레임 스크롤 상자 없음.
