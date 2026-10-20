import type { DocumentFile } from "./document";
import type { DocumentFormat } from "./documentFormats";
import { fileName } from "./documentFormats";
import { documentHtml } from "./documentHtml";

const PRINT_FRAME = "data-print-frame"; // 인쇄용 iframe 표시. 한 번에 하나만 둔다

function saveBlob(filename: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * 보이지 않는 iframe에 문서를 넣고 인쇄 창을 연다('PDF로 저장'). 새 창이 아니라 팝업 차단에 걸리지 않는다.
 * title이 저장 창의 기본 파일 이름이 된다. print()가 돌아오면 끝나고, 인쇄를 시작하지 못하면 거절한다.
 * 인쇄용 iframe은 afterprint에서 지우고, afterprint가 없는 브라우저는 다음 인쇄를 시작할 때 이전 것을 지운다.
 */
function printHtml(html: string, title: string): Promise<void> {
  document.querySelectorAll(`iframe[${PRINT_FRAME}]`).forEach((old) => old.remove());
  return new Promise((resolve, reject) => {
    const frame = document.createElement("iframe");
    frame.setAttribute(PRINT_FRAME, "");
    frame.setAttribute("aria-hidden", "true");
    frame.tabIndex = -1;
    frame.style.cssText = "position:fixed;right:0;bottom:0;width:0;height:0;border:0";
    frame.addEventListener(
      "load",
      () => {
        const win = frame.contentWindow;
        if (win === null) {
          frame.remove();
          return reject(new Error("인쇄 창을 열지 못했어요."));
        }
        try {
          win.document.title = title;
          win.addEventListener("afterprint", () => frame.remove(), { once: true });
          win.focus();
          win.print();
          resolve();
        } catch (error) {
          frame.remove();
          reject(error);
        }
      },
      { once: true },
    );
    frame.srcdoc = html;
    document.body.append(frame);
  });
}

/** 결과 문서를 고른 형식으로 내보낸다. 화면 밖 부수 효과라 App이 handlers에 넘긴다(테스트는 가짜를 넘긴다). Word 라이브러리는 이때 불러온다. */
export async function exportDocument({ basename, content }: DocumentFile, format: DocumentFormat): Promise<void> {
  if (format === "pdf") return printHtml(documentHtml(content), basename);
  if (format === "html") return saveBlob(fileName(basename, "html"), new Blob([documentHtml(content)], { type: "text/html;charset=utf-8" }));
  const [{ Packer }, { documentDocx }] = await Promise.all([import("docx"), import("./documentDocx")]);
  saveBlob(fileName(basename, "docx"), await Packer.toBlob(documentDocx(content)));
}
