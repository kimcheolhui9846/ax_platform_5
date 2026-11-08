import { describe, expect, it } from "vitest";
import { BACKEND_UNREACHABLE } from "../api/client";
import { createInventoryRunner } from "./requests";
import type { InventoryAction } from "./state";

const ok = <T>(data: T) => ({ data, response: new Response(null, { status: 200 }) });
const done = (data: string, seq: number): InventoryAction => ({ type: "failed", seq, message: `done:${data}` });

describe("createInventoryRunner", () => {
  it("요청 번호를 올리며 시작과 끝을 알린다", async () => {
    const actions: InventoryAction[] = [];
    const run = createInventoryRunner((a) => actions.push(a));
    await run({ kind: "load", request: async () => ok("a"), done });
    await run({ kind: "save", request: async () => ok("b"), done });
    expect(actions).toEqual([
      { type: "requested", seq: 1, kind: "load" },
      { type: "failed", seq: 1, message: "done:a" },
      { type: "requested", seq: 2, kind: "save" },
      { type: "failed", seq: 2, message: "done:b" },
    ]);
  });

  it("서버 오류는 detail 문장으로 실패시킨다", async () => {
    const actions: InventoryAction[] = [];
    const run = createInventoryRunner((a) => actions.push(a));
    const response = new Response(JSON.stringify({ detail: "수량이 이상해요" }), {
      status: 422,
      headers: { "content-type": "application/json" },
    });
    await run({ kind: "close", request: async () => ({ error: { detail: "수량이 이상해요" }, response }) as never, done });
    expect(actions[1]).toEqual({ type: "failed", seq: 1, message: "수량이 이상해요" });
  });

  it("예외면 BACKEND_UNREACHABLE", async () => {
    const actions: InventoryAction[] = [];
    const run = createInventoryRunner((a) => actions.push(a));
    await run({
      kind: "load",
      request: async () => {
        throw new Error("x");
      },
      done,
    });
    expect(actions[1]).toEqual({ type: "failed", seq: 1, message: BACKEND_UNREACHABLE });
  });
});
