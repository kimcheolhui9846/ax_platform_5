import { describe, expect, it } from "vitest";

import { toggleSelection } from "./selection";

describe("toggleSelection", () => {
  it("단일 선택은 항상 방금 고른 것 하나만 남긴다", () => {
    expect(toggleSelection(["a"], "b", false)).toEqual(["b"]);
    expect(toggleSelection(["a"], "a", false)).toEqual(["a"]);
  });

  it("다중 선택은 없던 항목을 추가한다", () => {
    expect(toggleSelection(["a"], "b", true)).toEqual(["a", "b"]);
  });

  it("다중 선택은 이미 있던 항목을 뺀다", () => {
    expect(toggleSelection(["a", "b"], "a", true)).toEqual(["b"]);
  });

  it("입력 배열을 바꾸지 않는다", () => {
    const before = ["a"];
    toggleSelection(before, "b", true);
    expect(before).toEqual(["a"]);
  });
});
