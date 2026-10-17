import { describe, expect, it } from "vitest";

import { STALE_NOTICE, actionState, confirmActions, REGENERATE_ACTION, saveButton } from "./actions";

describe("결과 버튼", () => {
  it("최신 아님 문구는 답뿐 아니라 보완 정보가 바뀐 경우도 아우른다", () => {
    expect(STALE_NOTICE).toBe("입력이 바뀌어 결과가 최신이 아니에요. 바뀐 내용을 반영하려면 초안을 다시 만들어 주세요.");
    expect(confirmActions({ has_result: true, result_stale: true })[0].label).toBe("바뀐 내용으로 초안 다시 만들기");
  });

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

  it("결과 화면 오른쪽의 다시 만들기는 보조 버튼이다", () => {
    expect(REGENERATE_ACTION).toEqual({ action: "generate", label: "초안 다시 만들기", primary: false });
  });

  it("처리 중이면 막고, 만들기는 생성할 수 없을 때도 막는다(보기는 LLM을 부르지 않는다)", () => {
    const generate = REGENERATE_ACTION;
    const show = { action: "show_result" as const, label: "결과 보기", primary: true };
    expect(actionState(generate, true, true)).toEqual({ label: "초안을 만드는 중…", disabled: true });
    expect(actionState(generate, false, false)).toEqual({ label: "초안 다시 만들기", disabled: true });
    expect(actionState(show, false, false)).toEqual({ label: "결과 보기", disabled: false });
    expect(actionState(show, true, true)).toEqual({ label: "결과 보기", disabled: true });
  });
});

describe("현재 버전 저장 버튼", () => {
  it("저장 전이고 최신이면 주 버튼, 저장했으면 막는다, 낡았으면 보조 버튼", () => {
    expect(saveButton({ saved: false }, false, false)).toEqual({ label: "현재 버전 저장", primary: true, disabled: false });
    expect(saveButton({ saved: false }, true, false)).toEqual({ label: "현재 버전 저장", primary: false, disabled: true });
    expect(saveButton({ saved: true }, false, false)).toEqual({ label: "저장한 버전이에요", primary: false, disabled: true });
  });

  it("근거를 붙인 결과는 출처와 함께 저장", () => {
    expect(saveButton({ saved: false }, false, true)).toEqual({ label: "출처와 함께 저장", primary: true, disabled: false });
  });
});
