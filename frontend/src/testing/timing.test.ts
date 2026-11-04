import { describe, expect, it } from "vitest";

import { median, medianMs } from "./timing";

describe("median", () => {
  it("홀수 개면 가운데 값이다", () => {
    expect(median([3, 1, 2])).toBe(2);
  });

  it("짝수 개면 가운데 두 값의 평균이다", () => {
    expect(median([4, 1, 3, 2])).toBe(2.5);
  });

  it("받은 배열은 바꾸지 않는다", () => {
    const values = [3, 1, 2];
    median(values);
    expect(values).toEqual([3, 1, 2]);
  });

  it("값이 없으면 오류다", () => {
    expect(() => median([])).toThrow();
  });
});

describe("medianMs", () => {
  it("데우기 횟수와 잴 횟수만큼 부른다", () => {
    let calls = 0;
    medianMs(() => { calls += 1; }, 10, 3);
    expect(calls).toBe(13);
  });

  it("걸린 시간은 0 이상의 밀리초다", () => {
    expect(medianMs(() => {}, 5, 0)).toBeGreaterThanOrEqual(0);
  });
});
