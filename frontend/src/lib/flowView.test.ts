import { describe, expect, it } from "vitest";

import { makeFlowItem, makeQuestion } from "../testing/factories";
import { firstEditable, flowNote, flowNumber, flowStatusLabel, isEditable, previousEditable, questionPosition } from "./flowView";

describe("isEditable", () => {
  it("답한 항목과 미정 항목만 고칠 수 있다", () => {
    const question = makeQuestion();
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
