import type { DocumentFile } from "./document";
import type { DocumentFormat } from "./documentFormats";
import { fileName } from "./documentFormats";
import { documentHtml } from "./documentHtml";

const PRINT_CLEANUP_MS = 60_000; // afterprint가 오지 않는 브라우저에서 인쇄용 iframe을 지울 때까지

function saveBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** 보이지 않는 iframe에 문서를 넣고 인쇄 창을 연다('PDF로 저장'). 새 창이 아니라 팝업 차단에 걸리지 않는다. */
function printHtml(html: string): void {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true");
  frame.tabIndex = -1;
  frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
  frame.addEventListener(
    "load",
    () => {
      const win = frame.contentWindow;
      if (win === null) return frame.remove();
      win.addEventListener("afterprint", () => frame.remove(), { once: true });
      window.setTimeout(() => frame.remove(), PRINT_CLEANUP_MS);
      win.focus();
      win.print();
    },
    { once: true },
  );
  frame.srcdoc = html;
  document.body.append(frame);
}

/** 결과 문서를 고른 형식으로 내보낸다. 화면 밖 부수 효과라 App이 handlers에 넘긴다(테스트는 가짜를 넘긴다). Word 라이브러리는 이때 불러온다. */
export async function exportDocument({ basename, content }: DocumentFile, format: DocumentFormat): Promise<void> {
  if (format === "pdf") return printHtml(documentHtml(content));
  if (format === "html") return saveBlob(fileName(basename, "html"), new Blob([documentHtml(content)], { type: "text/html;charset=utf-8" }));
  const [{ Packer }, { documentDocx }] = await Promise.all([import("docx"), import("./documentDocx")]);
  saveBlob(fileName(basename, "docx"), await Packer.toBlob(documentDocx(content)));
}
