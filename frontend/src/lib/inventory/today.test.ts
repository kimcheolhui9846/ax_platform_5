import { describe, expect, it } from "vitest";

import { localDateText } from "./format";

describe("localDateText", () => {
  it("로컬 날짜를 YYYY-MM-DD로", () => {
    expect(localDateText(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
    expect(localDateText(new Date(2026, 10, 8, 0, 1))).toBe("2026-11-08");
  });
});
