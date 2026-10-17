import { describe, expect, it } from "vitest";

import { makeResult, makeSession, makeTask, makeVersionView } from "../testing/factories";
import { assetWork, assetsToLoad, imageIdsOf, notInFlight } from "./assets";
import { initialState, reducer } from "./state";
import type { ScreenModel } from "./screenModel";

const withImages = (ids: string[]) => {
  const result = makeResult();
  return {
    ...result,
    result: {
      ...result.result,
      sections: [
        {
          order: 1,
          heading: "h",
          kind: "suggestion" as const,
          blocks: ids.map((id) => ({ type: "image" as const, asset_id: id, alt: "a", caption: "", origin: "ai_generated" as const })),
        },
      ],
    },
  };
};

describe("불러올 이미지", () => {
  it("결과가 보이는 화면의 이미지 id를 모은다", () => {
    const model: ScreenModel = { kind: "result", task: makeTask(), session: makeSession(), result: withImages(["a", "b"]), images: {} };
    expect(imageIdsOf(model)).toEqual(["a", "b"]);
    const version = makeVersionView({ result: withImages(["c"]).result });
    expect(imageIdsOf({ kind: "version", task: makeTask(), session: makeSession(), version, images: {} })).toEqual(["c"]);
    expect(imageIdsOf({ kind: "loading" })).toEqual([]);
  });

  it("이미 받았거나 부른 이미지는 다시 부르지 않는다", () => {
    const model: ScreenModel = { kind: "result", task: makeTask(), session: makeSession(), result: withImages(["a", "b", "c"]), images: {} };
    expect(assetsToLoad(model, { a: "data:x", b: null })).toEqual(["c"]);
  });
});

describe("notInFlight", () => {
  it("받는 중인 id는 고르지 않고, 끝나서 목록에서 빠진 id(세션을 떠났다 돌아온 경우)는 다시 고른다", () => {
    const inFlight = new Set(["a"]);
    expect(notInFlight(inFlight, ["a", "b"])).toEqual(["b"]);
    inFlight.delete("a");
    expect(notInFlight(inFlight, ["a", "b"])).toEqual(["a", "b"]);
  });
});

describe("받는 중에 세션을 떠났다 돌아온 경우", () => {
  it("요청은 다시 하고 내려받기는 다시 하지 않아, 늦게 온 응답이 받아들여진다", () => {
    const inFlight = new Set<string>();
    const model = (state: ReturnType<typeof initialState>): ScreenModel => ({
      kind: "result",
      task: makeTask(),
      session: makeSession(),
      result: withImages(["a"]),
      images: state.assets,
    });
    let state = initialState({ name: "result", sessionId: "sess_1" });

    let work = assetWork(assetsToLoad(model(state), state.assets), inFlight);
    expect(work).toEqual({ request: ["a"], fetch: ["a"] });
    work.request.forEach((assetId) => (state = reducer(state, { type: "assetRequested", assetId })));
    work.fetch.forEach((id) => inFlight.add(id)); // 내려받기 시작

    state = reducer(state, { type: "navigated", route: { name: "result", sessionId: "sess_2" } }); // 떠남: 이미지 비움
    expect(state.assets).toEqual({});
    state = reducer(state, { type: "navigated", route: { name: "result", sessionId: "sess_1" } }); // 돌아옴

    work = assetWork(assetsToLoad(model(state), state.assets), inFlight);
    expect(work).toEqual({ request: ["a"], fetch: [] }); // 받는 중이라 다시 내려받지는 않는다
    work.request.forEach((assetId) => (state = reducer(state, { type: "assetRequested", assetId })));

    state = reducer(state, { type: "assetLoaded", assetId: "a", url: "data:late" }); // 늦게 온 응답
    expect(state.assets).toEqual({ a: "data:late" });
  });
});
