import { useEffect, useMemo, useReducer } from "react";

import { Toast } from "../components/Toast";
import { readDraft, writeDraft } from "../lib/drafts";
import { isRouteHash, parseRoute, taskOf, toHash } from "../lib/routes";
import { browserStorage } from "../lib/storage";
import { makeHandlers } from "./handlers";
import { needsLoad } from "./load";
import { createRunner, startLoad } from "./requests";
import { screenModel } from "./screenModel";
import { initialState, isBusy, reducer } from "./state";
import { AppView, pageTitle } from "./view";

const TOAST_MS = 3500;

/** 앱 상태는 reducer 하나가 바꾼다. 여기서는 주소·불러오기·저장소·알림 같은 바깥과의 연결만 한다. */
export default function App() {
  const [state, dispatch] = useReducer(reducer, window.location.hash, (hash: string) => initialState(parseRoute(hash)));
  const run = useMemo(() => createRunner(dispatch), []);
  const storage = useMemo(browserStorage, []);

  // 주소 → 상태(뒤로 가기·직접 입력)
  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash;
      if (isRouteHash(hash)) dispatch({ type: "navigated", route: parseRoute(hash) });
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  // 상태 → 주소. 화면이 바뀌면 본문으로 초점을 옮기고 맨 위로 올린다.
  useEffect(() => {
    const hash = toHash(state.route);
    if (window.location.hash !== hash) window.location.hash = hash;
    document.getElementById("main")?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [state.route]);

  // 화면에 모자란 데이터 불러오기
  useEffect(() => {
    const load = needsLoad(state);
    if (load) void startLoad(run, load);
  }, [state, run]);

  // 쓰다 만 요청 글은 과제 화면에 처음 들어올 때 저장소에서 꺼낸다
  const task = taskOf(state.route);
  useEffect(() => {
    if (task !== null && !(task in state.drafts)) {
      dispatch({ type: "draftChanged", task, text: readDraft(storage, task) });
    }
  }, [task, state.drafts, storage]);

  // 알림은 잠시 뒤 닫는다
  useEffect(() => {
    if (state.toast === null) return;
    const timer = window.setTimeout(() => dispatch({ type: "toastClosed" }), TOAST_MS);
    return () => window.clearTimeout(timer);
  }, [state.toast]);

  const model = screenModel(state);
  const title = pageTitle(model);
  useEffect(() => {
    document.title = title;
  }, [title]);

  const on = makeHandlers({ state, run, dispatch, saveDraft: (key, text) => writeDraft(storage, key, text) });
  return (
    <>
      <AppView route={state.route} model={model} busy={isBusy(state)} on={on} />
      <Toast message={state.toast} />
    </>
  );
}
