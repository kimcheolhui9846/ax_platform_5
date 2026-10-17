import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { HOME } from "../lib/routes";
import { NOOP_HANDLERS } from "../preview/handlers";
import { makeFlowItem, makeForm, makeQuestion, makeResult, makeSession, makeTask } from "../testing/factories";
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
    const { main, side } = draw({ kind: "home", tasks: [task] });
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

  it("모드는 보낸 요청과 세 모드(상한 문구), 요청이 없으면 요청으로 안내", () => {
    const { main } = draw({ kind: "mode", task, form, draft: "수제 향초" });
    expect(main).toContain("수제 향초");
    expect(main).toContain("스탠다드 코칭 시작");
    expect(main).toContain("최대 10개");
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
    const { main, side } = draw({ kind: "result", task, session, result: makeResult() });
    expect(main).toContain("상품기획 초안");
    expect(side).toContain("질문 이어 가기");
    expect(side).toContain("기준 답변 바꾸기");
    const empty = draw({ kind: "result", task, session, result: null });
    expect(empty.main).toContain("아직 만든 결과가 없어요");
    expect(empty.side).toBeNull();
  });

  it("안내", () => {
    expect(draw({ kind: "guide" }).main).toContain("질문은 하나씩, 맥락은 끝까지");
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
    const html = renderToString(<AppView route={HOME} model={{ kind: "home", tasks: [task] }} busy on={NOOP_HANDLERS} />);
    expect(html).toContain('<button type="button" class="rail-help" disabled="">흐름 안내</button>');
    expect(html).toMatch(/<button type="button" class="btn" disabled="">과제 선택<\/button>/);
  });
});

describe("projectOf·pageTitle", () => {
  it("과제 화면은 과제 이름", () => {
    expect(projectOf({ kind: "home", tasks: [] })).toBeNull();
    expect(projectOf({ kind: "request", task, form, draft: "" })).toBe("상품기획");
    expect(pageTitle({ kind: "guide" })).toBe("창작자 AX");
    expect(pageTitle({ kind: "request", task, form, draft: "" })).toBe("창작자 AX · 상품기획");
  });
});
