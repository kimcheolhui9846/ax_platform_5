/**
 * 화면 주소(해시). 주소를 읽고 만드는 곳은 parseRoute·toHash 두 함수뿐이다.
 * 과제 화면(요청·모드)은 세션 전이라 과제 이름으로, 세션 화면은 세션 id로 연다.
 */
export type Route =
  | { name: "home" }
  | { name: "guide" }
  | { name: "work" }
  | { name: "documents" }
  | { name: "request"; task: string }
  | { name: "mode"; task: string }
  | { name: "question"; sessionId: string }
  | { name: "revise"; sessionId: string; questionId: string }
  | { name: "confirm"; sessionId: string }
  | { name: "result"; sessionId: string }
  | { name: "edit"; sessionId: string; order: number }
  | { name: "saved"; sessionId: string; version: number }
  | { name: "version"; sessionId: string; version: number };

export const HOME: Route = { name: "home" };

const TASK_VIEWS = new Set(["request", "mode"]);
const VERSION_NUMBER = /^[1-9]\d*$/;
const SECTION_ORDER = /^\d+$/;

function decode(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

/** 조각 하나로 된 공용 화면. */
function page(name: string): Route | null {
  switch (name) {
    case "guide":
      return { name: "guide" };
    case "work":
      return { name: "work" };
    case "documents":
      return { name: "documents" };
    default:
      return null;
  }
}

/** `#/s/{id}/{view}` 모양의 세션 화면. */
function sessionView(sessionId: string, view: string): Route | null {
  switch (view) {
    case "question":
      return { name: "question", sessionId };
    case "confirm":
      return { name: "confirm", sessionId };
    case "result":
      return { name: "result", sessionId };
    default:
      return null;
  }
}

/** [순수] 해시를 주소로. 모르는 모양은 홈이다. */
export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decode);
  const [first, second, third, fourth] = parts;
  if (parts.length === 1) return page(first) ?? HOME;
  if (parts.length === 2 && first !== "s" && TASK_VIEWS.has(second)) {
    return second === "request" ? { name: "request", task: first } : { name: "mode", task: first };
  }
  if (first === "s" && parts.length === 3) return sessionView(second, third) ?? HOME;
  if (first === "s" && parts.length === 4 && third === "question") {
    return { name: "revise", sessionId: second, questionId: fourth };
  }
  if (first === "s" && parts.length === 4 && VERSION_NUMBER.test(fourth)) {
    if (third === "v") return { name: "version", sessionId: second, version: Number(fourth) };
    if (third === "saved") return { name: "saved", sessionId: second, version: Number(fourth) };
  }
  if (first === "s" && parts.length === 4 && third === "edit" && SECTION_ORDER.test(fourth)) {
    return { name: "edit", sessionId: second, order: Number(fourth) };
  }
  return HOME;
}

/** [순수] 화면 주소인지. 본문 바로가기 같은 문서 안 앵커(#main)는 화면 이동이 아니다. */
export function isRouteHash(hash: string): boolean {
  return hash === "" || hash === "#" || hash.startsWith("#/");
}

/** [순수] 주소를 해시로. */
export function toHash(route: Route): string {
  const e = encodeURIComponent;
  switch (route.name) {
    case "home":
      return "#/";
    case "guide":
    case "work":
    case "documents":
      return `#/${route.name}`;
    case "request":
    case "mode":
      return `#/${e(route.task)}/${route.name}`;
    case "revise":
      return `#/s/${e(route.sessionId)}/question/${e(route.questionId)}`;
    case "version":
      return `#/s/${e(route.sessionId)}/v/${route.version}`;
    case "saved":
      return `#/s/${e(route.sessionId)}/saved/${route.version}`;
    case "edit":
      return `#/s/${e(route.sessionId)}/edit/${route.order}`;
    default:
      return `#/s/${e(route.sessionId)}/${route.name}`;
  }
}

/** [순수] 화면 묶음. 같은 묶음 안에서 옮기면 기다리던 요청을 그대로 받고, 묶음을 떠나면 늦은 응답을 버린다. */
export function contextOf(route: Route): string {
  switch (route.name) {
    case "home":
    case "guide":
    case "work":
    case "documents":
      return route.name;
    case "request":
    case "mode":
      return `task:${route.task}`;
    default:
      return `session:${route.sessionId}`;
  }
}

/** [순수] 내 세션 목록을 쓰는 화면(홈의 이어하기, 내 작업, 결과물). */
export function isListRoute(route: Route): boolean {
  return route.name === "home" || route.name === "work" || route.name === "documents";
}

export function taskOf(route: Route): string | null {
  return route.name === "request" || route.name === "mode" ? route.task : null;
}

export function sessionIdOf(route: Route): string | null {
  return "sessionId" in route ? route.sessionId : null;
}
