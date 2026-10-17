import { describe, expect, it } from "vitest";

import { formatDate } from "./format";

describe("formatDate", () => {
  it("한국 시각으로 보여 준다", () => {
    expect(formatDate("2026-10-16T09:05:00Z")).toBe("2026.10.16 18:05");
    expect(formatDate("2026-10-16T20:30:00+00:00")).toBe("2026.10.17 05:30");
  });

  it("읽을 수 없는 값은 그대로 둔다", () => {
    expect(formatDate("어제")).toBe("어제");
  });
});
