import { describe, expect, it } from "vitest";

import { menuAfter } from "./downloadMenu";

describe("menuAfter", () => {
  it("버튼을 누르면 열림이 뒤집힌다", () => {
    expect(menuAfter(false, "toggle")).toBe(true);
    expect(menuAfter(true, "toggle")).toBe(false);
  });

  it("형식을 고르거나 Esc·포커스 이탈·막힘이면 닫는다", () => {
    for (const event of ["choose", "escape", "blur", "disabled"] as const) {
      expect(menuAfter(true, event)).toBe(false);
      expect(menuAfter(false, event)).toBe(false);
    }
  });
});
