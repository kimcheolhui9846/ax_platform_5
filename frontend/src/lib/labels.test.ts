import { describe, expect, it } from "vitest";

import { cardLabel } from "./labels";

describe("cardLabel", () => {
  it("카드 유형을 한글로 바꾼다", () => {
    expect(cardLabel("diagnosis")).toBe("진단");
    expect(cardLabel("action")).toBe("실행 과제");
  });

  it("모르는 유형은 원문을 그대로 돌려준다", () => {
    expect(cardLabel("something_new")).toBe("something_new");
  });
});
