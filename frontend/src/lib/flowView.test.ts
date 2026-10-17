import { describe, expect, it } from "vitest";

import { makeFlowItem, makeQuestion } from "../testing/factories";
import { answeredBefore, firstEditable, flowNote, flowNumber, flowStatusLabel, isEditable, previousEditable, questionPosition } from "./flowView";

describe("isEditable", () => {
  it("답한·미정·멈춤 항목만 고칠 수 있다", () => {
    const question = makeQuestion();
    expect(isEditable(makeFlowItem({ status: "paused", question }))).toBe(true);
    expect(isEditable(makeFlowItem({ status: "answered", answer: "부모", question }))).toBe(true);
    expect(isEditable(makeFlowItem({ status: "skipped", question }))).toBe(true);
    expect(isEditable(makeFlowItem({ status: "current", question }))).toBe(false);
    expect(isEditable(makeFlowItem({ status: "upcoming" }))).toBe(false);
    expect(isEditable(makeFlowItem({ status: "answered", question: null }))).toBe(false);
  });
});

const answered = makeFlowItem({ field: "user", status: "answered", answer: "부모", question: makeQuestion({ question_id: "q_user" }) });
const skipped = makeFlowItem({ field: "usage", status: "skipped", question: makeQuestion({ question_id: "q_usage" }) });
const current = makeFlowItem({ field: "problem", status: "current", question: makeQuestion({ question_id: "q_problem" }) });
const upcoming = makeFlowItem({ field: "value", status: "upcoming" });

describe("흐름 표시", () => {
  it("상태 이름과 번호(01은 요청 정리)", () => {
    expect([answered, skipped, current, upcoming].map((i) => flowStatusLabel(i.status))).toEqual(["완료", "아직 미정", "현재 질문", "예정"]);
    expect([0, 1, 8].map(flowNumber)).toEqual(["02", "03", "10"]);
  });

  it("항목 아래 한 줄", () => {
    expect(flowNote(answered)).toBe("부모");
    expect(flowNote(skipped)).toBe("아직 미정으로 남겨 뒀어요.");
    expect(flowNote(current)).toBe("답변을 기다리고 있어요.");
    expect(flowNote(upcoming)).toBe("차례가 오면 물어볼게요.");
  });

  it("이전 단계는 지금 질문 바로 앞의 고칠 수 있는 질문이다", () => {
    expect(previousEditable([answered, skipped, current, upcoming])).toBe("q_usage");
    expect(previousEditable([current, upcoming])).toBeNull();
    expect(previousEditable([answered, skipped])).toBe("q_usage");
  });

  it("답변 바꾸기는 처음 고칠 수 있는 질문이다", () => {
    expect(firstEditable([answered, skipped, current])).toBe("q_user");
    expect(firstEditable([current, upcoming])).toBeNull();
  });

  it("진행 수는 물어본 질문과 지금 질문을 센다", () => {
    expect(questionPosition([answered, skipped, current, upcoming], 5)).toBe("질문 3/5");
    expect(questionPosition([answered, skipped], 5)).toBe("질문 2/5 · 마침");
    expect(questionPosition([], 3)).toBe("질문 0/3 · 마침");
  });
});

describe("멈춘 필드와 질문 제목", () => {
  const paused = makeFlowItem({ field: "usage", status: "paused", question: makeQuestion({ question_id: "q_usage" }) });

  it("멈춤은 이어 가면 다시 묻는다고 알린다", () => {
    expect(flowStatusLabel("paused")).toBe("잠시 멈춤");
    expect(flowNote(paused)).toBe("이어 가면 다시 물어볼게요.");
  });

  it("지금 질문이 없어도 멈춘 필드나 예정이 있으면 마치지 않았다", () => {
    expect(questionPosition([answered, paused, upcoming], 5)).toBe("질문 2/5");
    expect(questionPosition([answered, upcoming], 5)).toBe("질문 1/5");
    expect(questionPosition([answered], 5)).toBe("질문 1/5 · 마침");
  });

  it("지금 질문 앞에 답한(미정·멈춤 포함) 필드 수", () => {
    expect(answeredBefore([current, upcoming])).toBe(0); // '원래 예시 보기'로 돌아온 첫 질문도 첫 질문이다
    expect(answeredBefore([answered, skipped, paused, current])).toBe(3);
  });
});
