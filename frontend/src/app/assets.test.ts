import { describe, expect, it } from "vitest";

import { makeResult, makeSession, makeTask, makeVersionView } from "../testing/factories";
import { assetsToLoad, claimAssets, imageIdsOf } from "./assets";
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

describe("claimAssets", () => {
  it("이미 부른 id는 다시 고르지 않는다", () => {
    const requested = new Set<string>();
    expect(claimAssets(requested, ["a", "b"])).toEqual(["a", "b"]);
    expect(claimAssets(requested, ["a", "b"])).toEqual([]);
    expect(claimAssets(requested, ["b", "c"])).toEqual(["c"]);
  });
});
