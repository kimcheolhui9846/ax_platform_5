import type { TaskSummary } from "../api/types";
import { documentContent } from "../lib/document";
import type { Shown } from "../lib/document";
import { documentHtml } from "../lib/documentHtml";
import { versionIsStale } from "../lib/sessions";
import type { DocumentFile } from "../lib/documentHtml";
import type { ScreenModel } from "./screenModel";

function fileFor(task: TaskSummary, request: string, shown: Shown, stale: boolean): DocumentFile {
  return {
    filename: `AX_${task.task_type}_V${shown.version.version}.html`,
    html: documentHtml({ ...documentContent(task, shown, stale), request }),
  };
}

/** [순수] 지금 화면에서 내려받을 문서. 결과가 보이는 화면(결과·저장 완료·버전 보기)에만 있다. */
export function documentFileOf(model: ScreenModel): DocumentFile | null {
  switch (model.kind) {
    case "result":
      return model.result === null ? null : fileFor(model.task, model.session.raw_input, model.result, model.session.result_stale);
    case "saved":
    case "version":
      return fileFor(model.task, model.session.raw_input, model.version, versionIsStale(model.version, model.session));
    default:
      return null;
  }
}
