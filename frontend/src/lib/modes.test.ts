import { describe, expect, it } from "vitest";

import { MODE_COPY, RECOMMENDED_MODE, modeName } from "./modes";

describe("모드 문구", () => {
  it("이름과 상한 문구", () => {
    expect(["quick", "standard", "precise"].map((m) => modeName(m as "quick"))).toEqual(["빠른", "스탠다드", "정밀"]);
    expect(MODE_COPY.standard.detail(5)).toContain("최대 5개");
    expect(MODE_COPY.precise.detail(10)).toContain("최대 10개");
    expect(RECOMMENDED_MODE).toBe("standard");
  });
});
