import { describe, expect, it } from "vitest";

import { actionState, confirmActions, regenerateAction } from "./actions";

describe("결과 버튼", () => {
  it("결과가 없으면 만들기 하나", () => {
    expect(confirmActions({ has_result: false, result_stale: false })).toEqual([
      { action: "generate", label: "맞아요 · 이 정보로 초안 만들기", primary: true },
    ]);
  });

  it("최신 결과가 있으면 보기가 먼저, 낡았으면 다시 만들기가 먼저", () => {
    expect(confirmActions({ has_result: true, result_stale: false }).map((a) => [a.action, a.primary])).toEqual([
      ["show_result", true],
      ["generate", false],
    ]);
    expect(confirmActions({ has_result: true, result_stale: true }).map((a) => [a.action, a.primary])).toEqual([
      ["generate", true],
      ["show_result", false],
    ]);
  });

  it("결과 화면의 다시 만들기는 낡았을 때만 주 버튼이다", () => {
    expect(regenerateAction(true)).toEqual({ action: "generate", label: "바뀐 답으로 다시 만들기", primary: true });
    expect(regenerateAction(false)).toEqual({ action: "generate", label: "초안 다시 만들기", primary: false });
  });

  it("처리 중이면 막고, 만들기는 생성할 수 없을 때도 막는다(보기는 LLM을 부르지 않는다)", () => {
    const generate = regenerateAction(false);
    const show = { action: "show_result" as const, label: "결과 보기", primary: true };
    expect(actionState(generate, true, true)).toEqual({ label: "초안을 만드는 중…", disabled: true });
    expect(actionState(generate, false, false)).toEqual({ label: "초안 다시 만들기", disabled: true });
    expect(actionState(show, false, false)).toEqual({ label: "결과 보기", disabled: false });
    expect(actionState(show, true, true)).toEqual({ label: "결과 보기", disabled: true });
  });
});
