import type { LabeledResult } from "../api/types";
import type { Images } from "../lib/document";
import type { ScreenModel } from "./screenModel";

function shownResult(model: ScreenModel): LabeledResult | null {
  switch (model.kind) {
    case "result":
      return model.result?.result ?? null;
    case "edit":
    case "evidence":
      return model.result.result;
    case "saved":
    case "version":
      return model.version.result;
    default:
      return null;
  }
}

/** [순수] 지금 화면이 그릴 결과 이미지의 id(섹션 순서대로). */
export function imageIdsOf(model: ScreenModel): string[] {
  return (shownResult(model)?.sections ?? []).flatMap((s) => s.blocks.flatMap((b) => (b.type === "image" ? [b.asset_id] : [])));
}

/** [순수] 아직 받지도 부르지도 않은 이미지. 실패한 것(null)은 다시 부르지 않는다. */
export function assetsToLoad(model: ScreenModel, assets: Images): string[] {
  return imageIdsOf(model).filter((id) => !(id in assets));
}

/**
 * [순수] 이미지를 받을 때 effect가 할 일. 상태에 '받는 중'을 적는 요청(request)은 부를 id마다 언제나 하고,
 * 실제 내려받기(fetch)만 받는 중이 아닌 id로 거른다. 받는 중에 세션을 떠났다 돌아오면 상태의 이미지는 비었지만
 * 내려받기는 아직 도는 중이라, 요청을 다시 해 두어야 늦게 온 응답(assetLoaded)이 받아들여진다.
 */
export function assetWork(pending: string[], inFlight: ReadonlySet<string>): { request: string[]; fetch: string[] } {
  return { request: pending, fetch: notInFlight(inFlight, pending) };
}

/** [순수] 지금 받는 중이 아닌 id만 고른다(StrictMode가 effect를 두 번 돌려도 같은 이미지를 두 번 받지 않으려고). 받기가 끝나면 호출한 쪽이 받는 중 목록에서 뺀다. */
export function notInFlight(inFlight: ReadonlySet<string>, ids: string[]): string[] {
  return ids.filter((id) => !inFlight.has(id));
}
