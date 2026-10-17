import type { DocumentFile } from "./documentHtml";

/** 브라우저에서 파일로 내려받는다. 화면 밖 부수 효과라 App이 handlers에 넘긴다(테스트는 가짜를 넘긴다). */
export function saveFile({ filename, html }: DocumentFile): void {
  const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
