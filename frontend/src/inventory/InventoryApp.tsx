import { useEffect, useMemo, useReducer, useRef } from "react";

import { Toast } from "../components/Toast";
import type { RailProps } from "../layout/Rail";
import { localDateText } from "../lib/inventory/format";
import type { InventoryTab } from "../lib/routes";
import { TOAST_MS } from "../lib/toast";
import { loadRequest, makeInventoryHandlers } from "./handlers";
import { createInventoryRunner } from "./requests";
import { inventoryScreen } from "./screen";
import { initialInventoryState, inventoryReducer } from "./state";
import { InventoryView } from "./view";

type Props = {
  tab: InventoryTab;
  rail: RailProps;
  onTab: (tab: InventoryTab) => void;
  confirmLeave: () => boolean;
};

/** 왼쪽 메뉴로 옮길 때도 저장하지 않은 입력을 묻는다. */
function guardedRail(rail: RailProps, leave: (go: () => void) => void): RailProps {
  const guide = rail.onGuide;
  return { ...rail, onNavigate: (key) => leave(() => rail.onNavigate(key)), onGuide: guide && (() => leave(guide)) };
}

/** 재고 화면(코칭과 상태를 섞지 않는다). 상태는 reducer 하나, 여기서는 불러오기·알림 같은 바깥과의 연결만 한다(문서 제목은 App이 정한다). */
export function InventoryApp({ tab, rail, onTab, confirmLeave }: Props) {
  const [state, dispatch] = useReducer(inventoryReducer, undefined, () => initialInventoryState(localDateText(new Date())));
  const run = useMemo(() => createInventoryRunner(dispatch), []); // 한 번만 만든다(요청 번호가 다시 시작하지 않게)

  // 처음 들어오면 불러온다(StrictMode의 effect 두 번 실행에도 한 번만)
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void run(loadRequest());
  }, [run]);

  useEffect(() => {
    if (state.toast === null) return;
    const timer = window.setTimeout(() => dispatch({ type: "toastClosed" }), TOAST_MS);
    return () => window.clearTimeout(timer);
  }, [state.toast]);

  const on = makeInventoryHandlers({ state, tab, run, dispatch, navigate: onTab, newRequestId: () => "manual:" + crypto.randomUUID(), confirmLeave });
  return (
    <>
      <InventoryView tab={tab} model={inventoryScreen(state, tab)} busy={state.inflight?.kind ?? null} on={on} rail={guardedRail(rail, on.onLeave)} />
      <Toast message={state.toast} />
    </>
  );
}
