import type {
  EvidenceItem,
  Question,
  ResultSection,
  ResultView,
  SessionContext,
  SessionSummary,
  SessionView,
  TaskForm,
  TaskSummary,
  VersionView,
} from "../api/types";
import type { Images } from "../lib/document";
import { carryKey, nextTask } from "../lib/carry";
import { isEditable } from "../lib/flowView";
import type { EditableFlowItem } from "../lib/flowView";
import type { AppState } from "./state";

/** 지금 그릴 화면과 그 화면에 필요한 값. 화면은 이 값만 보고 그린다. */
export type ScreenModel =
  | { kind: "loading" }
  | { kind: "unavailable" }
  | { kind: "home"; tasks: TaskSummary[]; sessions: SessionSummary[] }
  | { kind: "guide" }
  | { kind: "work"; sessions: SessionSummary[] }
  | { kind: "documents"; sessions: SessionSummary[] }
  | { kind: "request"; task: TaskSummary; form: TaskForm; draft: string; context: SessionContext | null; carryFailed: boolean; noticeAcknowledged: boolean }
  | { kind: "mode"; task: TaskSummary; form: TaskForm; draft: string; context: SessionContext | null; carryFailed: boolean; noticeAcknowledged: boolean }
  | { kind: "question"; task: TaskSummary; session: SessionView; question: Question }
  | { kind: "revise"; task: TaskSummary; session: SessionView; item: EditableFlowItem }
  | { kind: "generating"; task: TaskSummary; session: SessionView }
  | { kind: "failed"; task: TaskSummary; session: SessionView }
  | { kind: "confirm"; task: TaskSummary; session: SessionView }
  | { kind: "result"; task: TaskSummary; session: SessionView; result: ResultView | null; images: Images }
  | { kind: "edit"; task: TaskSummary; session: SessionView; result: ResultView; section: ResultSection; images: Images }
  | { kind: "evidence"; task: TaskSummary; session: SessionView; result: ResultView; items: EvidenceItem[] }
  | { kind: "saved"; task: TaskSummary; session: SessionView; version: VersionView; images: Images; next: TaskSummary | null }
  | { kind: "version"; task: TaskSummary; session: SessionView; version: VersionView; images: Images };

const LOADING: ScreenModel = { kind: "loading" };

/** [순수] 지금 그릴 화면. 데이터가 모자라면 loading, 불러오기가 실패했으면 unavailable이다. */
export function screenModel(state: AppState): ScreenModel {
  const model = resolve(state);
  return model.kind === "loading" && state.stalled !== null ? { kind: "unavailable" } : model;
}

function resolve(state: AppState): ScreenModel {
  const { route } = state;
  switch (route.name) {
    case "home": {
      // 내 세션 목록을 못 받았어도 홈은 이어하기 없이 연다(새 과제는 시작할 수 있다)
      const sessions = state.sessions ?? (state.stalled === "sessions" ? [] : null);
      return state.tasks === null || sessions === null ? LOADING : { kind: "home", tasks: state.tasks, sessions };
    }
    case "guide":
      return { kind: "guide" };
    case "work":
    case "documents":
      if (state.sessions === null) return LOADING;
      return route.name === "work" ? { kind: "work", sessions: state.sessions } : { kind: "documents", sessions: state.sessions };
    case "request":
    case "mode": {
      const task = findTask(state.tasks, route.task);
      if (task === null || state.form === null || state.form.task_type !== route.task) return LOADING;
      // 이어 가는 화면은 가져올 내용 미리보기가 올 때까지 기다린다. 못 받았으면 가져오지 않고 계속할 수 있게 연다
      const from = route.from;
      const key = from !== null ? carryKey(route.task, from) : null;
      const loaded = key !== null && state.carry?.key === key;
      const carryFailed = key !== null && !loaded && state.stalled === `carry:${key}`;
      if (key !== null && !loaded && !carryFailed) return LOADING;
      const context = loaded ? (state.carry?.context ?? null) : null;
      const data = { task, form: state.form, draft: state.drafts[route.task] ?? "", context, carryFailed, noticeAcknowledged: state.notices[route.task] === true };
      return route.name === "request" ? { kind: "request", ...data } : { kind: "mode", ...data };
    }
    default: {
      const session = state.session;
      if (session === null || session.session_id !== route.sessionId) return LOADING;
      const task = findTask(state.tasks, session.task_type);
      if (task === null) return LOADING;
      // 초안을 만드는 동안은 어느 세션 화면이든 생성 중 화면이다(주소는 그대로)
      if (state.inflight?.generating) return { kind: "generating", task, session };
      if (route.name === "failed") return { kind: "failed", task, session };
      if (route.name === "version" || route.name === "saved") {
        const version = state.version;
        const loaded = version !== null && version.session_id === session.session_id && version.version.version === route.version;
        if (!loaded) return LOADING;
        // 저장하지 않은 번호로 저장 완료 주소를 열었으면(직접 입력·북마크) 버전 보기로 보여 준다
        const saved = route.name === "saved" && version.version.saved;
        return saved ? { kind: "saved", task, session, version, images: state.assets, next: nextTask(state.tasks ?? [], task.task_type) }
          : { kind: "version", task, session, version, images: state.assets };
      }
      if (route.name === "result" || route.name === "edit" || route.name === "evidence") {
        if (!session.has_result) return { kind: "result", task, session, result: null, images: state.assets };
        const result = state.result !== null && state.result.session_id === session.session_id ? state.result : null;
        if (result === null) return LOADING;
        if (route.name === "evidence") {
          const evidence = state.evidence !== null && state.evidence.sessionId === session.session_id ? state.evidence : null;
          return evidence === null ? LOADING : { kind: "evidence", task, session, result, items: evidence.items };
        }
        // 없는 섹션 번호로 문구 수정 주소를 열었으면(직접 입력·지난 주소) 결과 화면으로 보여 준다
        const section = route.name === "edit" ? result.result.sections.find((s) => s.order === route.order) : undefined;
        return section
          ? { kind: "edit", task, session, result, section, images: state.assets }
          : { kind: "result", task, session, result, images: state.assets };
      }
      if (route.name === "revise") {
        const item = session.flow.find((i) => i.question?.question_id === route.questionId);
        if (item !== undefined && isEditable(item)) return { kind: "revise", task, session, item };
      }
      if (route.name !== "confirm" && session.next_question !== null) {
        return { kind: "question", task, session, question: session.next_question };
      }
      return { kind: "confirm", task, session };
    }
  }
}

function findTask(tasks: TaskSummary[] | null, taskType: string): TaskSummary | null {
  return tasks?.find((t) => t.task_type === taskType) ?? null;
}
