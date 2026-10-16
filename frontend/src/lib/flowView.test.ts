import { describe, expect, it } from "vitest";

import { makeFlowItem, makeQuestion } from "../testing/factories";
import { isEditable } from "./flowView";

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
