import { describe, expect, it } from "vitest";

import { sourceLabel } from "./labels";

describe("sourceLabel", () => {
  it("알려진 출처는 한글 라벨을 돌려준다", () => {
    expect(sourceLabel("user_free_text")).toBe("직접 입력");
    expect(sourceLabel("ai_assumption")).toBe("AI 가정");
  });

  it("모르는 출처는 원문을 그대로 돌려준다", () => {
    expect(sourceLabel("something_new")).toBe("something_new");
  });
});
