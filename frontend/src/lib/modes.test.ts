import { describe, expect, it } from "vitest";

import { MODE_COPY, RECOMMENDED_MODE, modeName } from "./modes";

describe("모드 문구", () => {
  it("이름과 추천 모드", () => {
    expect(["quick", "standard", "precise"].map((m) => modeName(m as "quick"))).toEqual(["빠른", "스탠다드", "정밀"]);
    expect(RECOMMENDED_MODE).toBe("standard");
  });

  it("질문 수를 쓰지 않는다(상한은 진행 표시가 알린다)", () => {
    expect(MODE_COPY.quick.detail).toBe("꼭 필요한 질문으로 방향을 잡고, 주요 기준을 확인해 초안을 만들어요.");
    expect(MODE_COPY.standard.detail).toBe("질문을 주고받으며 아이디어와 실행 기준을 차근차근 구체화해요.");
    expect(MODE_COPY.precise.detail).toBe("배경과 세부 조건을 살펴보며, 제약과 판단 근거까지 확인해요.");
    for (const copy of Object.values(MODE_COPY)) expect(copy.detail).not.toMatch(/\d/);
  });
});
