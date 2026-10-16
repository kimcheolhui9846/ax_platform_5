import { describe, expect, it } from "vitest";

import { assumptionKey, formatAssumption } from "./assumption";

const base = { field: "user", label: "사용자", value: "30대 직장인", reason: "처음 입력에서 추출", requires_confirmation: true };

describe("formatAssumption", () => {
  it("내부 필드 이름 대신 라벨을 보여 준다", () => {
    expect(formatAssumption(base)).toBe("사용자: 30대 직장인 (확인 필요)");
  });

  it("확인이 필요 없으면 표시를 붙이지 않는다", () => {
    expect(formatAssumption({ ...base, requires_confirmation: false })).toBe("사용자: 30대 직장인");
  });
});

describe("assumptionKey", () => {
  it("같은 필드가 두 번 나와도 키가 겹치지 않는다", () => {
    expect(assumptionKey(base, 0)).not.toBe(assumptionKey(base, 1));
  });
});
