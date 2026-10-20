import { useId, useRef, useState } from "react";

import { menuAfter } from "../lib/downloadMenu";
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
  // 막히면 열림을 바로 거둔다(렌더 중 상태 맞춤). 남겨 두면 다시 풀릴 때 저절로 열린다.
  if (disabled && open) setOpen(menuAfter(open, "disabled"));
  const shown = open && !disabled;
  // 목록을 눌러도 포커스가 옮겨 가지 않게 한다(Safari는 버튼을 눌러도 포커스를 주지 않는다). blur로 닫히기 전에 클릭이 닿게 한다.
  const buttonClass = full ? "btn full" : "btn";
  const close = (event: "choose" | "escape") => {
    setOpen(menuAfter(open, event));
    opener.current?.focus();
  };
  return (
    <div
      className="download-menu stack8"
      onKeyDown={(event) => {
        if (event.key === "Escape" && shown) {
          event.stopPropagation();
          close("escape");
        }
      }}
      onBlur={(event) => {
        // 바깥으로 포커스가 나가면(바깥 클릭·Tab) 포커스는 옮기지 않고 닫는다.
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(menuAfter(open, "blur"));
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
        onClick={() => setOpen(menuAfter(open, "toggle"))}
      >
        문서 내려받기
      </button>
      {shown && (
        <ul id={listId} className="download-options stack8" aria-label="내려받을 형식" onMouseDown={(event) => event.preventDefault()}>
          {DOCUMENT_FORMATS.map(({ format, label }) => (
            <li key={format}>
              <button
                type="button"
                className={buttonClass}
                onClick={() => {
                  close("choose");
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
