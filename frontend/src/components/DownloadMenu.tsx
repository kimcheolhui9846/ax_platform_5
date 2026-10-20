import { useId, useRef, useState } from "react";

import { DOCUMENT_FORMATS } from "../lib/documentFormats";
import type { DocumentFormat } from "../lib/documentFormats";

type Props = {
  onDownload: (format: DocumentFormat) => void;
  disabled?: boolean;
  describedBy?: string; // 막힌 이유 안내(최신 아님)
  full?: boolean; // 오른쪽 패널처럼 버튼을 한 줄 가득
  initialOpen?: boolean; // 미리보기 갤러리에서 연 상태를 그릴 때
};

/** '문서 내려받기' 버튼과 형식 목록(펼침). 열림은 이 부품 안에서 끝나는 UI 상태라 여기서 가진다. 고르거나 Esc로 닫으면 버튼으로 포커스를 돌려준다. */
export function DownloadMenu({ onDownload, disabled = false, describedBy, full = false, initialOpen = false }: Props) {
  const [open, setOpen] = useState(initialOpen);
  const opener = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const shown = open && !disabled;
  const buttonClass = full ? "btn full" : "btn";
  const close = () => {
    setOpen(false);
    opener.current?.focus();
  };
  return (
    <div
      className="download-menu stack8"
      onKeyDown={(event) => {
        if (event.key === "Escape" && shown) {
          event.stopPropagation();
          close();
        }
      }}
    >
      <button
        ref={opener}
        type="button"
        className={buttonClass}
        disabled={disabled}
        aria-expanded={shown}
        aria-controls={shown ? listId : undefined}
        aria-describedby={describedBy}
        onClick={() => setOpen(!open)}
      >
        문서 내려받기
      </button>
      {shown && (
        <ul id={listId} className="download-options stack8" aria-label="내려받을 형식">
          {DOCUMENT_FORMATS.map(({ format, label }) => (
            <li key={format}>
              <button
                type="button"
                className={buttonClass}
                onClick={() => {
                  close();
                  onDownload(format);
                }}
              >
                {label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
