import { describe, expect, it } from "vitest";

import { formatProgress } from "./progress";

describe("formatProgress", () => {
  it("질문 수와 준비도를 한 줄로 만든다", () => {
    expect(formatProgress({ asked: 2, cap: 7, readiness: 0.5 })).toBe("질문 2/7 · 준비도 50%");
  });

  it("준비도는 반올림한다", () => {
    expect(formatProgress({ asked: 0, cap: 5, readiness: 0.666 })).toBe("질문 0/5 · 준비도 67%");
    expect(formatProgress({ asked: 1, cap: 5, readiness: 0.004 })).toBe("질문 1/5 · 준비도 0%");
  });
});
