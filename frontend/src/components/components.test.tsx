import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { criteriaRows } from "../lib/criteria";
import type { EditableFlowItem } from "../lib/flowView";
import { makeFlowItem, makeQuestion, makeResult, makeSession } from "../testing/factories";
import { Composer } from "./Composer";
import { CriteriaBox } from "./CriteriaBox";
import { FlowPanel } from "./FlowPanel";
import { FlowSummary } from "./FlowSummary";
import { QuestionCard } from "./QuestionCard";
import { ResultDocument } from "./ResultDocument";
import { ReviseCard } from "./ReviseCard";
import { Toast } from "./Toast";

const noop = () => {};

describe("Composer", () => {
  const html = (value: string, busy: boolean) =>
    renderToString(
      <Composer label="내 생각" value={value} placeholder="적어 주세요" rows={2} maxLength={100} submitLabel="전송" busy={busy} onChange={noop} onSubmit={noop} />,
    );

  it("빈 글이거나 처리 중이면 보낼 수 없다", () => {
    expect(html("  ", false)).toContain('<button type="submit" class="btn primary send" disabled="">');
    expect(html("향초", true)).toContain('<button type="submit" class="btn primary send" disabled="">');
    expect(html("향초", false)).toContain('<button type="submit" class="btn primary send">');
  });

  it("라벨이 입력창을 가리킨다", () => {
    const rendered = html("", false);
    const id = /<label for="([^"]+)"/.exec(rendered)?.[1];
    expect(id).toBeTruthy();
    expect(rendered).toContain(`<textarea id="${id}"`);
  });
});

describe("QuestionCard", () => {
  const card = (question = makeQuestion(), kicker = "핵심 질문") =>
    renderToString(
      <QuestionCard question={question} kicker={kicker} request="수제 향초" busy={false} onAnswer={noop} onExample={noop} onEarlyDraft={noop} />,
    );

  it("요청·제목·선택지·도움 버튼을 그린다", () => {
    const html = card();
    expect(html).toContain("수제 향초");
    expect(html).toContain("◈ AI 코치 · 핵심 질문");
    expect(html).toContain("20~30대 1인 가구");
    expect(html).toContain("다른 예시 보기");
    expect(html).not.toContain("원래 예시 보기");
    expect(html).toContain("아직 모르겠어요");
    expect(html).toContain("현재 정보로 초안 만들기");
    expect(html).not.toContain("aria-pressed");
  });

  it("사다리 질문에는 원래 예시 보기가 있다", () => {
    expect(card(makeQuestion({ level: 1 }), "다른 예시")).toContain("원래 예시 보기");
  });

  it("여러 개 고르는 질문은 눌림 표시와 보내기 버튼이 있다", () => {
    const html = card(makeQuestion({ multi_select: true }));
    expect(html).toContain('aria-pressed="false"');
    expect(html).toContain("고른 답 보내기");
  });

  it("AI가 제안한 선택지를 표시한다", () => {
    const html = card(makeQuestion({ options: [{ id: "p4_1", label: "가방 정리", ai_suggested: true }], level: 4, is_ai_proposal: true }));
    expect(html).toContain("AI 제안");
  });
});

describe("ReviseCard", () => {
  const item = (patch: Partial<EditableFlowItem>): EditableFlowItem => ({
    ...makeFlowItem({ status: "answered", answer: "부모" }),
    question: makeQuestion(),
    ...patch,
  });

  it("지금 답을 입력창에 채워 둔다", () => {
    const html = renderToString(<ReviseCard item={item({})} busy={false} onRevise={noop} onCancel={noop} />);
    expect(html).toContain("◈ 답변 고치기 · 사용자");
    expect(html).toContain("지금 답: 부모");
    expect(html).toMatch(/<textarea[^>]*>부모<\/textarea>/);
    expect(html).toContain("고치지 않고 돌아가기");
  });

  it("다른 예시를 보던 중에 멈춘 질문은 그렇다고 안내한다(빈 '지금 답'을 보이지 않는다)", () => {
    const html = renderToString(<ReviseCard item={item({ status: "paused", answer: null })} busy={false} onRevise={noop} onCancel={noop} />);
    expect(html).toContain("다른 예시를 보던 중에 멈춘 질문이에요");
    expect(html).not.toContain("지금 답:");
  });

  it("미정으로 둔 질문은 지금 답할 수 있다고 안내한다", () => {
    const html = renderToString(<ReviseCard item={item({ status: "skipped", answer: null })} busy={false} onRevise={noop} onCancel={noop} />);
    expect(html).toContain("아직 미정으로 남겨 둔 질문이에요");
  });
});

describe("FlowPanel", () => {
  const flow = [
    makeFlowItem({ field: "user", label: "사용자", status: "answered", answer: "부모", question: makeQuestion({ question_id: "q_user" }) }),
    makeFlowItem({ field: "usage", label: "사용 상황", status: "skipped", question: makeQuestion({ question_id: "q_usage" }) }),
    makeFlowItem({ field: "problem", label: "고객 문제", status: "current", question: makeQuestion({ question_id: "q_problem" }) }),
    makeFlowItem({ field: "value", label: "핵심 가치", status: "upcoming" }),
  ];
  const panel = (atConfirm: boolean, onPrevious: (() => void) | null) =>
    renderToString(
      <FlowPanel modeLabel="스탠다드" position="질문 3/5" request="수제 향초" flow={flow} atConfirm={atConfirm} busy={false} onEdit={noop} onPrevious={onPrevious} />,
    );

  it("요청 → 질문(번호·상태) → 답변 확인 순서로 그린다", () => {
    const html = panel(false, noop);
    expect(html).toContain("스탠다드 · 질문 3/5");
    expect(html).toContain("01 요청 정리 · 완료");
    expect(html).toContain("02 사용자 · 완료");
    expect(html).toContain("03 사용 상황 · 아직 미정");
    expect(html).toContain("04 고객 문제 · 현재 질문");
    expect(html).toContain("05 핵심 가치 · 예정");
    expect(html).toContain('aria-current="step"');
    expect(html).toContain("다음 · 답변 확인 → 초안 만들기");
    expect(html).toContain("← 이전 단계");
  });

  it("답한·미정 항목만 고칠 수 있다", () => {
    const html = panel(false, null);
    expect(html.match(/답변 수정"/g)).toHaveLength(2);
    expect(html).toContain('aria-label="사용자 답변 수정"');
    expect(html).not.toContain("← 이전 단계");
  });

  it("답변 확인 화면에서는 확인이 현재 단계다", () => {
    expect(panel(true, null)).toContain("현재 · 답변 확인 → 초안 만들기");
  });
});

describe("FlowSummary·CriteriaBox", () => {
  it("답한 질문만 요약한다", () => {
    const html = renderToString(
      <FlowSummary flow={[makeFlowItem({ label: "사용자", status: "answered", answer: "부모" }), makeFlowItem({ label: "사용 상황", status: "skipped" }), makeFlowItem({ status: "upcoming", label: "예정 항목" })]} />,
    );
    expect(html).toContain("부모");
    expect(html).toContain("아직 미정");
    expect(html).not.toContain("예정 항목");
    const paused = renderToString(<FlowSummary flow={[makeFlowItem({ label: "사용 상황", status: "paused" })]} />);
    expect(paused).toContain("사용 상황");
    expect(paused).toContain("잠시 멈춤");
    expect(renderToString(<FlowSummary flow={[]} />)).toContain("아직 답한 질문이 없어요.");
  });

  it("기준 상자는 값과 출처를 보여 준다", () => {
    const { summary } = makeSession();
    const html = renderToString(<CriteriaBox rows={criteriaRows(summary, [{ field: "mvp", label: "MVP 구성" }])} />);
    expect(html).toContain("내 답변에서 반영한 기준");
    expect(html).toContain("수제 향초");
    expect(html).toContain(" · 직접 입력");
    expect(html).toContain("아직 미정");
  });
});

describe("ResultDocument", () => {
  it("제목·기준·번호 매긴 섹션·가정·검토 항목", () => {
    const result = makeResult({
      validation: { issues: [{ rule: "r", message: "근거 없는 숫자가 있어요.", severity: "warning" }], passed: true },
    });
    result.result.assumptions = [{ field: "price", label: "가격 방향", value: "1~3만원", reason: "", requires_confirmation: true }];
    const html = renderToString(<ResultDocument result={result} title="상품기획 초안" kicker="상품 콘셉트 · 첫 제작 기획서" rows={[]} />);
    expect(html).toContain("상품기획 초안");
    expect(html).toContain("상품 콘셉트 · 첫 제작 기획서");
    expect(html).toContain('<span class="section-number">01</span>');
    expect(html).toContain("진단");
    expect(html).toContain("가격 방향: 1~3만원 (확인 필요)");
    expect(html).toContain("근거 없는 숫자가 있어요.");
  });
});

describe("Toast", () => {
  it("알림이 없으면 숨기되 읽기 영역은 남긴다", () => {
    expect(renderToString(<Toast message={null} />)).toContain('hidden=""');
    const html = renderToString(<Toast message="저장했어요." />);
    expect(html).toContain('aria-live="polite"');
    expect(html).toContain("저장했어요.");
    expect(html).not.toContain("hidden");
  });
});
