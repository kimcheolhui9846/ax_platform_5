import type { ReactNode } from "react";

import { Header } from "./Header";
import type { HeaderProps } from "./Header";
import { Rail } from "./Rail";
import type { RailProps } from "./Rail";

type Props = {
  rail: RailProps;
  header: HeaderProps;
  side?: ReactNode | null;
  children: ReactNode;
};

/** 디자인 V2의 뼈대. 왼쪽 메뉴 | 헤더 / 본문 + 오른쪽 패널. 내용은 props로만 받는다. */
export function AppShell({ rail, header, side = null, children }: Props) {
  return (
    <div className="app-shell">
      <a href="#main" className="skip">
        본문으로 바로가기
      </a>
      <Rail {...rail} />
      <div className="app-frame">
        <Header {...header} />
        <div className="app-body">
          <main id="main" className="app-main" tabIndex={-1}>
            {children}
          </main>
          {side !== null && <aside className="app-side">{side}</aside>}
        </div>
      </div>
    </div>
  );
}
