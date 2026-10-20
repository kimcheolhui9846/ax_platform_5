import type { TaskSummary } from "../api/types";
import { documentContent } from "../lib/document";
import { safeFileName } from "../lib/fileName";
import type { DocumentFile, Images, Shown } from "../lib/document";
import { versionIsStale } from "../lib/sessions";
import type { ScreenModel } from "./screenModel";

function fileFor(task: TaskSummary, name: string, request: string, shown: Shown, stale: boolean, images: Images): DocumentFile {
  return {
    basename: `${safeFileName(name, `AX_${task.task_type}`)}_V${shown.version.version}`,
    content: { ...documentContent(task, shown, stale, images), request },
  };
}

/** [순수] 지금 화면에서 내려받을 문서. 결과가 보이는 화면(결과·저장 완료·버전 보기)에만 있다. */
export function documentFileOf(model: ScreenModel): DocumentFile | null {
  switch (model.kind) {
    case "result":
      return model.result === null ? null : fileFor(model.task, model.session.name, model.session.raw_input, model.result, model.session.result_stale, model.images);
    case "saved":
    case "version":
      return fileFor(model.task, model.session.name, model.session.raw_input, model.version, versionIsStale(model.version, model.session), model.images);
    default:
      return null;
  }
}
