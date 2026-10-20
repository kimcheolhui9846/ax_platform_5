import { describe, expect, it } from "vitest";

import { makeTask } from "../testing/factories";
import { carryIsFrom, carryKey, nextTask } from "./carry";

const TASKS = [
  makeTask({ task_type: "business_plan", title: "사업계획" }),
  makeTask({ task_type: "product_planning", title: "상품기획" }),
  makeTask({ task_type: "marketing_content", title: "마케팅 콘텐츠" }),
];

describe("nextTask", () => {
  it("다음 과제, 마지막 다음은 처음", () => {
    expect(nextTask(TASKS, "business_plan")?.title).toBe("상품기획");
    expect(nextTask(TASKS, "marketing_content")?.title).toBe("사업계획");
  });

  it("모르는 과제나 과제가 하나뿐이면 null", () => {
    expect(nextTask(TASKS, "nope")).toBeNull();
    expect(nextTask([TASKS[0]], "business_plan")).toBeNull();
  });
});

it("carryIsFrom은 키의 세션이 같을 때만 참이다", () => {
  const key = carryKey("branding", { sessionId: "s1", version: 2 });
  expect(carryIsFrom(key, "s1")).toBe(true);
  expect(carryIsFrom(key, "s")).toBe(false);
  expect(carryIsFrom(key, "branding")).toBe(false);
});

it("carryKey는 과제·세션·버전을 잇는다", () => {
  expect(carryKey("branding", { sessionId: "s1", version: 2 })).toBe("branding:s1:2");
});
