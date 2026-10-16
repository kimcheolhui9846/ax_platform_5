import type { ReactNode } from "react";

import { Header } from "./Header";
import type { HeaderProps } from "./Header";
import { Rail } from "./Rail";
import type { RailProps } from "./Rail";

type Props = {
  rail: RailProps;
  header: HeaderProps;
  side?: ReactNode | null;
  /** 본문 id. 한 페이지에 뼈대를 여러 개 그리는 미리보기에서만 바꾼다. */
  mainId?: string;
  children: ReactNode;
};

/**
 * 디자인 V2의 뼈대. 왼쪽 메뉴 | 헤더 / 본문 + 오른쪽 패널. 내용은 props로만 받는다.
 * 바깥 app-viewport가 폭 기준 컨테이너라 창이 아니라 뼈대가 놓인 폭으로 배치가 바뀐다(미리보기 프레임도 같다).
 */
export function AppShell({ rail, header, side = null, mainId = "main", children }: Props) {
  return (
    <div className="app-viewport">
      <div className="app-shell">
        <a href={`#${mainId}`} className="skip">
          본문으로 바로가기
        </a>
        <Rail {...rail} />
        <div className="app-frame">
          <Header {...header} />
          <div className="app-body">
            <main id={mainId} className="app-main" tabIndex={-1}>
              {children}
            </main>
            {side !== null && <aside className="app-side">{side}</aside>}
          </div>
        </div>
      </div>
    </div>
  );
}
