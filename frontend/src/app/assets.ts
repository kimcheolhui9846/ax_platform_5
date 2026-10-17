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
