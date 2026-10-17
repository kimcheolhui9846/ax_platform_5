import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { STALE_NOTICE, STALE_SAVE_HINT } from "../lib/actions";
import { HOME } from "../lib/routes";
import { NOOP_HANDLERS } from "../preview/handlers";
import { makeFlowItem, makeForm, makeQuestion, makeResult, makeSession, makeSessionSummary, makeTask, makeVersionView } from "../testing/factories";
import type { ScreenModel } from "./screenModel";
import { AppView, pageTitle, projectOf, renderScreen } from "./view";

const task = makeTask();
const form = makeForm();
const answered = makeFlowItem({ status: "answered", answer: "부모", question: makeQuestion({ question_id: "q_0" }) });

function draw(model: ScreenModel, busy = false) {
  const { main, side } = renderScreen(model, busy, NOOP_HANDLERS);
  return { main: renderToString(main), side: side === null ? null : renderToString(side) };
}

describe("renderScreen", () => {
  it("불러오는 중·불러오지 못함", () => {
    expect(draw({ kind: "loading" }).main).toContain("불러오는 중이에요");
    const unavailable = draw({ kind: "unavailable" });
    expect(unavailable.main).toContain("다시 시도");
    expect(unavailable.side).toBeNull();
  });

  it("홈은 과제 카드", () => {
    const { main, side } = draw({ kind: "home", tasks: [task], sessions: [] });
    expect(main).toContain("만들고 싶은 상품을 구체화하고 싶어요");
    expect(main).toContain("완성할 것 · 상품 콘셉트 · 첫 제작 기획서");
    expect(main).toContain("상품기획 시작하기 →");
    expect(side).toBeNull();
  });

  it("요청은 입력창과 예시", () => {
    const { main } = draw({ kind: "request", task, form, draft: "" });
    expect(main).toContain("상품기획에서 어떤 도움이 필요한가요?");
    expect(main).toContain('placeholder="예) 집들이 선물용 수제 향초"');
    expect(main).toContain("이 문장 넣기");
  });

  it("모드는 보낸 요청과 세 모드(질문 수 없이), 요청이 없으면 요청으로 안내", () => {
    const { main } = draw({ kind: "mode", task, form, draft: "수제 향초" });
    expect(main).toContain("수제 향초");
    expect(main).toContain("스탠다드 코칭 시작");
    expect(main).toContain("꼭 필요한 질문으로 방향을 잡고");
    expect(main).not.toContain("최대 10개");
    expect(draw({ kind: "mode", task, form, draft: " " }).main).toContain("먼저 요청을 보내 주세요");
    expect(draw({ kind: "mode", task, form, draft: "x" }, true).main).toContain("코칭을 준비하는 중…");
  });

  it("질문은 질문 카드와 흐름 패널", () => {
    const session = makeSession();
    const { main, side } = draw({ kind: "question", task, session, question: session.next_question! });
    expect(main).toContain("◈ AI 코치 · 핵심 질문");
    expect(side).toContain("스탠다드 · 질문 1/5");
    expect(side).toContain("02 사용자 · 현재 질문");
  });

  it("답 고치기는 고치기 카드와 흐름 패널", () => {
    const session = makeSession({ flow: [answered] });
    const { main, side } = draw({ kind: "revise", task, session, item: { ...answered, question: answered.question! } });
    expect(main).toContain("◈ 답변 고치기 · 사용자");
    expect(side).toContain("질문과 답변 흐름");
  });

  it("답변 확인은 기준·결과 이름·버튼과 흐름 패널(확인이 현재 단계)", () => {
    const session = makeSession({ next_question: null, flow: [answered] });
    const { main, side } = draw({ kind: "confirm", task, session });
    expect(main).toContain("이렇게 이해했어요. 맞나요?");
    expect(main).toContain("상품 콘셉트 · 첫 제작 기획서");
    expect(main).toContain("맞아요 · 이 정보로 초안 만들기");
    expect(main).toContain("답변 바꿀게요");
    expect(main).not.toContain("남은 질문에 마저 답하기");
    expect(side).toContain("현재 · 답변 확인 → 초안 만들기");
  });

  it("질문이 남은 채 확인하면 남은 질문으로 돌아갈 수 있다", () => {
    expect(draw({ kind: "confirm", task, session: makeSession() }).main).toContain("남은 질문에 마저 답하기");
  });

  it("결과는 문서와 다음 할 일, 결과가 없으면 답변 확인으로 안내", () => {
    const session = makeSession({ next_question: null, has_result: true, flow: [answered] });
    const { main, side } = draw({ kind: "result", task, session, result: makeResult(), images: {} });
    expect(main).toContain("상품기획 초안");
    expect(side).toContain("질문 이어 가기");
    expect(side).toContain("기준 답변 바꾸기");
    const empty = draw({ kind: "result", task, session, result: null, images: {} });
    expect(empty.main).toContain("아직 만든 결과가 없어요");
    expect(empty.side).toBeNull();
  });

  it("안내", () => {
    expect(draw({ kind: "guide" }).main).toContain("질문은 하나씩, 맥락은 끝까지");
  });

  it("홈은 과제마다 진행 중인 세션이 있으면 이어하기와 새로 시작을 보인다", () => {
    const sessions = [makeSessionSummary({ task_type: "product_planning" })];
    const { main } = draw({ kind: "home", tasks: [task], sessions });
    expect(main).toContain("진행 중인 상품기획 이어하기 →");
    expect(main).toContain("새로 시작하기");
    expect(main).toContain("내 작업 보기");
    expect(draw({ kind: "home", tasks: [task], sessions: [] }).main).toContain("상품기획 시작하기 →");
    const finished = [makeSessionSummary({ has_question: false, has_result: true })];
    expect(draw({ kind: "home", tasks: [task], sessions: finished }).main).toContain("상품기획 결과 이어 보기 →");
  });

  it("내 작업은 세션마다 진행 단계와 이어서 작업하기, 없으면 빈 안내", () => {
    const sessions = [makeSessionSummary({ raw_input: "한글 파우치", has_question: false, has_result: true, latest_version: 2 })];
    const { main, side } = draw({ kind: "work", sessions });
    expect(main).toContain("한글 파우치 · 상품기획");
    expect(main).toContain("스탠다드 · 결과 V2 · 2026.10.16 18:00");
    expect(main).toContain("이어서 작업하기 →");
    expect(side).toBeNull();
    expect(draw({ kind: "work", sessions: [] }).main).toContain("아직 시작한 작업이 없어요");
  });

  it("결과물은 저장한 버전마다 열기, 없으면 빈 안내", () => {
    const saved = { version: 2, created_at: "2026-10-16T10:00:00Z", reason: "regenerate" as const, saved: true };
    const { main } = draw({ kind: "documents", sessions: [makeSessionSummary({ saved_versions: [saved] })] });
    expect(main).toContain("상품기획 초안 · V2");
    expect(main).toContain("V2 · 다시 만든 초안 · 2026.10.16 19:00");
    expect(main).toContain("이 버전 열기 →");
    expect(draw({ kind: "documents", sessions: [makeSessionSummary()] }).main).toContain("아직 저장한 결과가 없어요");
  });

  it("결과 화면 오른쪽에 현재 버전 저장과 문서 내려받기", () => {
    const session = makeSession({ next_question: null, has_result: true });
    const { main, side } = draw({ kind: "result", task, session, result: makeResult(), images: {} });
    expect(main).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
    expect(side).toContain("현재 버전 저장");
    expect(side).toContain("문서 내려받기");
    const savedResult = makeResult({ version: { version: 1, created_at: "2026-10-16T09:00:00Z", reason: "first", saved: true } });
    expect(draw({ kind: "result", task, session, result: savedResult, images: {} }).side).toContain("저장한 버전이에요");
  });

  it("낡은 결과는 본문 위 배너, 저장·내려받기는 막고 이유를 보인다", () => {
    const stale = makeSession({ next_question: null, has_result: true, result_stale: true });
    const { main, side } = draw({ kind: "result", task, session: stale, result: makeResult(), images: {} });
    expect(main).toContain('role="status"');
    expect(main).toContain("결과가 최신이 아니에요");
    expect(main).toContain("바뀐 내용으로 다시 만들기");
    expect(main.indexOf("stale-banner")).toBeLessThan(main.indexOf("상품기획 초안"));
    expect(side).toContain(STALE_SAVE_HINT);
    expect(side).not.toContain(STALE_NOTICE);
    expect(side).toMatch(/<button[^>]*disabled=""[^>]*>현재 버전 저장</);
    expect(side).toMatch(/<button[^>]*disabled=""[^>]*>문서 내려받기</);
    const fresh = draw({ kind: "result", task, session: makeSession({ next_question: null, has_result: true }), result: makeResult(), images: {} });
    expect(fresh.main).not.toContain("stale-banner");
    expect(fresh.side).not.toContain(STALE_SAVE_HINT);
    expect(fresh.side).not.toMatch(/<button[^>]*disabled=""[^>]*>문서 내려받기</);
  });

  it("저장 완료는 결과물·다시 보기·내려받기", () => {
    const session = makeSession({ next_question: null, has_result: true });
    const { main, side } = draw({ kind: "saved", task, session, version: makeVersionView(), images: {} });
    expect(main).toContain("✓ 저장 완료");
    expect(main).toContain("상품기획 초안을 저장했어요.");
    expect(main).toContain("결과물 목록 보기");
    expect(main).toContain("저장한 결과 다시 보기");
    expect(main).toContain("문서 내려받기");
    expect(side).toContain("질문 흐름");
  });

  it("버전 보기는 보기 전용 안내와 그 버전 문서", () => {
    const session = makeSession({ next_question: null, has_result: true });
    const old = makeVersionView({ latest: false });
    const { main, side } = draw({ kind: "version", task, session, version: old, images: {} });
    expect(main).toContain("보기 전용 · 지난 버전이에요");
    expect(main).toContain("현재 버전으로");
    expect(main).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서 · 최신 아님");
    expect(side).toContain("문서 내려받기");
    expect(draw({ kind: "version", task, session, version: makeVersionView(), images: {} }).main).toContain("지금 결과와 같은 버전이에요.");
    const changed = makeSession({ next_question: null, has_result: true, result_stale: true });
    expect(draw({ kind: "version", task, session: changed, version: makeVersionView(), images: {} }).main).toContain(
      "지금 결과와 같은 버전이에요. 답이 바뀌어 최신은 아니에요.",
    );
  });
});

describe("renderScreen — 보완·문구 수정", () => {
  const supplements = [{ name: "material", label: "소재", example: "", value: null }];

  it("결과 오른쪽에 미확인 정보와 소개 문구 수정하기", () => {
    const session = makeSession({ has_result: true, supplements });
    const { side } = draw({ kind: "result", task, session, result: makeResult(), images: {} });
    expect(side).toContain("미확인 정보 채우기");
    expect(side).toContain("소개 문구 수정하기");
  });

  it("문구 수정은 수정 카드와 흐름 요약·미확인 정보", () => {
    const session = makeSession({ has_result: true, supplements });
    const result = makeResult();
    const { main, side } = draw({ kind: "edit", task, session, result, section: result.result.sections[0], images: {} });
    expect(main).toContain("문구 반영하기");
    expect(side).toContain("미확인 정보 채우기");
  });
});

describe("AppView", () => {
  it("헤더 과제 이름·단계와 왼쪽 메뉴까지 그린다", () => {
    const session = makeSession();
    const html = renderToString(
      <AppView
        route={{ name: "question", sessionId: "sess_1" }}
        model={{ kind: "question", task, session, question: session.next_question! }}
        busy={false}
        on={NOOP_HANDLERS}
      />,
    );
    expect(html).toContain('<div class="header-project">상품기획</div>');
    expect(html).toContain('<span class="header-step is-current">2 함께 구체화</span>');
    expect(html).toContain("app-side");
  });

  it("요청 중에는 메뉴·과제 선택·흐름 안내를 막는다", () => {
    const html = renderToString(<AppView route={HOME} model={{ kind: "home", tasks: [task], sessions: [] }} busy on={NOOP_HANDLERS} />);
    expect(html).toContain('<button type="button" class="rail-help" disabled="">흐름 안내</button>');
    expect(html).toMatch(/<button type="button" class="btn" disabled="">과제 선택<\/button>/);
  });
});

describe("projectOf·pageTitle", () => {
  it("과제 화면은 과제 이름", () => {
    expect(projectOf({ kind: "home", tasks: [], sessions: [] })).toBeNull();
    expect(projectOf({ kind: "request", task, form, draft: "" })).toBe("상품기획");
    expect(pageTitle({ kind: "guide" })).toBe("창작자 AX");
    expect(pageTitle({ kind: "request", task, form, draft: "" })).toBe("창작자 AX · 상품기획");
  });
});

describe("renderScreen — 근거 검토", () => {
  const evidenceRecord = {
    source_id: "z",
    title: "제작 점검 항목",
    text: "여닫기를 점검합니다.",
    note: "제품 시험 전",
    source_title: "지퍼 사용상 주의",
    publisher: "YKK KOREA",
    url: "https://ykkkorea.com/a",
    section_kind: "suggestion" as const,
    section_order: 1,
  };

  it("자료가 있는 과제의 결과 화면에는 근거 검토 버튼이 있고, 없는 과제에는 없다", () => {
    const session = makeSession({ has_result: true });
    const withSources = draw({ kind: "result", task: makeTask({ evidence_sources: 2 }), session, result: makeResult(), images: {} });
    expect(withSources.side).toContain("근거 자료 검토 · 2건");
    const without = draw({ kind: "result", task: makeTask({ evidence_sources: 0 }), session, result: makeResult(), images: {} });
    expect(without.side).not.toContain("근거 자료");
  });

  it("근거를 반영한 버전은 제목·다시 보기·반영 전 보기·출처 저장 버튼을 보인다", () => {
    const base = makeResult();
    const result = makeResult({
      version: { version: 3, created_at: "2026-10-16T09:00:00Z", reason: "evidence", saved: false },
      result: { ...base.result, evidence: [evidenceRecord] },
    });
    const { side } = draw({ kind: "result", task: makeTask({ evidence_sources: 2 }), session: makeSession({ has_result: true }), result, images: {} });
    expect(side).toContain("검토 내용을 반영했어요");
    expect(side).toContain("근거 자료 다시 보기");
    expect(side).toContain("근거 반영 전 보기");
    expect(side).toContain("출처와 함께 저장");
  });

  it("evidence 모델은 근거 검토 화면을 그린다", () => {
    const { main, side } = draw({ kind: "evidence", task, session: makeSession({ has_result: true }), result: makeResult(), items: [] });
    expect(main).toContain('aria-label="근거 검토"');
    expect(side).toContain("결과에 반영할 내용");
  });
});
