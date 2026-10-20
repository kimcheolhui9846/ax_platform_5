import { describe, expect, it } from "vitest";

import { safeFileName } from "./fileName";

describe("safeFileName", () => {
  it("보통 이름은 그대로 쓴다", () => {
    expect(safeFileName("수제 향초", "AX_x")).toBe("수제 향초");
  });

  it("파일 이름에 못 쓰는 문자와 제어문자를 뺀다", () => {
    expect(safeFileName('a\\b/c:d*e?f"g<h>i|j', "AX_x")).toBe("abcdefghij");
    expect(safeFileName("a\u0000b\u001fc\u007fd", "AX_x")).toBe("abcd");
  });

  it("공백은 하나로 접고 앞뒤 공백과 끝의 점을 지운다", () => {
    expect(safeFileName("  a   b\t\nc  ", "AX_x")).toBe("a b c");
    expect(safeFileName("보고서..", "AX_x")).toBe("보고서");
    expect(safeFileName(" 보고서. . ", "AX_x")).toBe("보고서");
  });

  it("40자까지만 쓴다", () => {
    expect(safeFileName("가".repeat(50), "AX_x")).toBe("가".repeat(40));
  });

  it("40자 경계의 이모지를 반으로 자르지 않는다", () => {
    const text = "가".repeat(39) + "😀😀";
    expect(safeFileName(text, "AX_x")).toBe("가".repeat(39) + "😀");
  });

  it("비면 대체 이름을 쓴다", () => {
    expect(safeFileName("", "AX_x")).toBe("AX_x");
    expect(safeFileName(' / : * ? " ', "AX_x")).toBe("AX_x");
    expect(safeFileName("...", "AX_x")).toBe("AX_x");
  });
});
