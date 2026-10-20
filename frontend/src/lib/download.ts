import type { DocumentFile } from "./document";
import { fileName } from "./documentFormats";
import { documentHtml } from "./documentHtml";

/** 브라우저에서 파일로 내려받는다. 화면 밖 부수 효과라 App이 handlers에 넘긴다(테스트는 가짜를 넘긴다). */
export function saveFile({ basename, content }: DocumentFile): void {
  const url = URL.createObjectURL(new Blob([documentHtml(content)], { type: "text/html;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName(basename, "html");
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
