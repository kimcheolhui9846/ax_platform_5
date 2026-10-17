import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";

import type { SupplementItem } from "../api/types";
import { criteriaRows } from "../lib/criteria";
import type { EditableFlowItem } from "../lib/flowView";
import { documentContent } from "../lib/document";
import { EditMain } from "../screens/EditScreen";
import { makeFlowItem, makeQuestion, makeResult, makeSession, makeTask } from "../testing/factories";
import { Composer } from "./Composer";
import { CriteriaBox } from "./CriteriaBox";
import { FlowPanel } from "./FlowPanel";
import { FlowSummary } from "./FlowSummary";
import { QuestionCard } from "./QuestionCard";
import { ResultDocument } from "./ResultDocument";
import { ReviseCard } from "./ReviseCard";
import { SupplementForm } from "./SupplementForm";
import { SupplementPanel } from "./SupplementPanel";
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
    const result = makeResult();
    result.result.assumptions = [{ field: "price", label: "가격 방향", value: "1~3만원", reason: "", requires_confirmation: true }];
    const html = renderToString(
      <ResultDocument
        title="상품기획 초안"
        kicker="V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서"
        rows={[]}
        result={result.result}
        issues={[{ rule: "r", message: "근거 없는 숫자가 있어요.", severity: "warning" }]}
        supplements={[]}
      />,
    );
    expect(html).toContain("상품기획 초안");
    expect(html).toContain("V1 · 첫 초안 / 상품 콘셉트 · 첫 제작 기획서");
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

const items: SupplementItem[] = [
  { name: "material", label: "소재", example: "면 100%", value: "면" },
  { name: "size", label: "크기", example: "", value: null },
];

describe("SupplementPanel", () => {
  const html = (changed: boolean, current = items, canGenerate = true, apply: (() => void) | null = noop) =>
    renderToString(<SupplementPanel current={current} applied={[]} changed={changed} canGenerate={canGenerate} busy={false} onSave={noop} onApply={apply} />);

  it("입력 상태와 미확인 항목을 보이고, 반영할 것이 있을 때만 초안에 반영을 누를 수 있다", () => {
    expect(html(true)).toContain("입력 1/2 · 아직 초안에 미반영");
    expect(html(true)).toContain("미확인: 크기");
    expect(html(true)).toContain('<button type="button" class="btn">초안에 반영</button>');
    expect(html(false)).toContain('<button type="button" class="btn" disabled="">초안에 반영</button>');
  });

  it("지금 생성할 수 없으면 바뀌었어도 초안에 반영을 누를 수 없다", () => {
    expect(html(true, items, false)).toContain('<button type="button" class="btn" disabled="">초안에 반영</button>');
  });

  it("onApply가 null이면 초안에 반영 버튼을 그리지 않는다(문구 수정 화면)", () => {
    const out = html(true, items, true, null);
    expect(out).not.toContain("초안에 반영</button>");
    expect(out).toContain("정보 입력·수정");
  });

  it("대화상자는 닫힌 채로 시작한다(양식을 그리지 않는다)", () => {
    expect(html(true)).toContain("<dialog");
    expect(html(true)).not.toContain("입력 내용 저장");
  });

  it("보완 항목이 없는 과제면 그리지 않는다", () => {
    expect(html(false, [])).toBe("");
  });
});

describe("SupplementForm", () => {
  const html = renderToString(<SupplementForm titleId="t" items={items} busy={false} onSave={noop} onCancel={noop} />);

  it("저장 중에는 닫기·취소도 누를 수 없다(저장이 끝나야 닫힌다)", () => {
    const saving = renderToString(<SupplementForm titleId="t" items={items} busy={true} onSave={noop} onCancel={noop} />);
    expect(saving).toMatch(/<button type="button" class="btn compact" aria-label="정보 입력 닫기" disabled="">/);
    expect(saving).toContain('<button type="button" class="btn" disabled="">취소</button>');
  });

  it("항목마다 지금 값(미확인은 빈 칸)과 예시 넣기·미확인으로", () => {
    expect(html).toContain('<h2 id="t">미확인 정보를 채워 주세요</h2>');
    expect(html).toContain('value="면"');
    expect(html).toContain('placeholder="미확인"');
    expect(html.match(/미확인으로/g)).toHaveLength(2);
  });

  it("열면 첫 입력칸에만 포커스가 간다", () => {
    expect(html.match(/autofocus/g)).toHaveLength(1);
    expect(html.indexOf("autofocus")).toBeLessThan(html.indexOf('placeholder="미확인"', html.indexOf("autofocus") + 1));
    expect(html).toMatch(/<input[^>]*id="t-material"[^>]*autofocus|<input[^>]*autofocus[^>]*id="t-material"/);
  });

  it("예시가 없는 항목은 예시 넣기를 누를 수 없다", () => {
    expect(html.match(/<button type="button" class="btn compact" disabled="">예시 넣기<\/button>/g)).toHaveLength(1);
  });

  it("검증 전임을 알리고 저장·취소가 있다", () => {
    expect(html).toContain("예시값을 선택해도 사실 검증이 완료된 것은 아니에요.");
    expect(html).toContain("입력 내용 저장");
    expect(html).toContain('aria-label="정보 입력 닫기"');
  });
});

describe("ResultDocument — 보완 정보", () => {
  it("반영한 보완 정보는 검증 전으로 따로 보인다", () => {
    const content = { ...documentContent(makeTask(), makeResult(), false), supplements: [{ label: "소재", value: "면" }] };
    const html = renderToString(<ResultDocument {...content} />);
    expect(html).toContain("보완 정보 · 사용자 입력 / 검증 전");
    expect(html).toContain("<span>소재</span><span>면</span>");
  });
});

describe("EditMain", () => {
  const section = { order: 1, heading: "상품 콘셉트", kind: "diagnosis" as const, blocks: [{ type: "text" as const, text: "한글 파우치 소개" }] };

  it("지금 문구를 보이고 입력창을 그 문구로 채운다", () => {
    const html = renderToString(<EditMain section={section} busy={false} onSubmit={noop} onBack={noop} />);
    expect(html).toContain("상품 콘셉트");
    expect(html.match(/한글 파우치 소개/g)).toHaveLength(2); // 지금 문구와 입력창
    expect(html).toMatch(/maxlength="2500"/i);
    expect(html).toContain("문구 반영하기");
    expect(html).toContain("← 결과로 돌아가기");
  });

  it("글이 지금 문구와 같으면 문구 반영하기를 누를 수 없다", () => {
    const html = renderToString(<EditMain section={section} busy={false} onSubmit={noop} onBack={noop} />);
    expect(html).toMatch(/<button type="submit"[^>]*disabled=""[^>]*>문구 반영하기/);
  });
});
