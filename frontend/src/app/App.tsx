import { useEffect, useMemo, useReducer, useState } from "react";

import { Toast } from "../components/Toast";
import { saveFile } from "../lib/download";
import { readDraft, writeDraft } from "../lib/drafts";
import { carryScreenOf, isRouteHash, parseRoute, taskOf, toHash } from "../lib/routes";
import { browserStorage } from "../lib/storage";
import { makeHandlers } from "./handlers";
import { needsLoad } from "./load";
import { assetWork, assetsToLoad } from "./assets";
import { createRunner, loadAsset, startLoad } from "./requests";
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
  // 결과 이미지는 화면 불러오기와 따로, 그릴 이미지마다 한 번씩 받는다(받는 중인 id는 끝날 때까지 적어 두어 StrictMode에서도 두 번 받지 않는다)
  const [inFlightAssets] = useState(() => new Set<string>());
  // 목록은 렌더마다 새 배열이라 의존성으로 쓰면 effect가 매번 돈다. 같은 목록이면 같은 문자열이 되도록 id를 이어 붙여 의존성으로 둔다.
  const pendingAssets = assetsToLoad(model, state.assets).join(" ");
  useEffect(() => {
    const work = assetWork(pendingAssets.split(" ").filter(Boolean), inFlightAssets);
    for (const assetId of work.request) dispatch({ type: "assetRequested", assetId });
    for (const assetId of work.fetch) {
      inFlightAssets.add(assetId);
      void loadAsset(assetId)
        .then((url) => dispatch({ type: "assetLoaded", assetId, url }))
        .finally(() => inFlightAssets.delete(assetId));
    }
  }, [pendingAssets, inFlightAssets]);

  const title = pageTitle(model);
  useEffect(() => {
    document.title = title;
  }, [title]);

  const on = makeHandlers({
    state,
    carryScreen: carryScreenOf(state.route),
    run,
    dispatch,
    saveDraft: (key, text) => writeDraft(storage, key, text),
    saveFile,
  });
  return (
    <>
      <AppView route={state.route} model={model} busy={isBusy(state)} on={on} />
      <Toast message={state.toast} />
    </>
  );
}
