/**
 * 화면 주소(해시). 주소를 읽고 만드는 곳은 parseRoute·toHash 두 함수뿐이다.
 * 과제 화면(요청·모드)은 세션 전이라 과제 이름으로, 세션 화면은 세션 id로 연다.
 */
export type Route =
  | { name: "home" }
  | { name: "guide" }
  | { name: "request"; task: string }
  | { name: "mode"; task: string }
  | { name: "question"; sessionId: string }
  | { name: "revise"; sessionId: string; questionId: string }
  | { name: "confirm"; sessionId: string }
  | { name: "result"; sessionId: string };

export const HOME: Route = { name: "home" };

const TASK_VIEWS = new Set(["request", "mode"]);
const SESSION_VIEWS = new Set(["question", "confirm", "result"]);

function decode(segment: string): string {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

/** [순수] 해시를 주소로. 모르는 모양은 홈이다. */
export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decode);
  const [first, second, third, fourth] = parts;
  if (parts.length === 1 && first === "guide") return { name: "guide" };
  if (parts.length === 2 && first !== "s" && TASK_VIEWS.has(second)) {
    return second === "request" ? { name: "request", task: first } : { name: "mode", task: first };
  }
  if (first === "s" && parts.length === 3 && SESSION_VIEWS.has(third)) {
    if (third === "question") return { name: "question", sessionId: second };
    return third === "confirm" ? { name: "confirm", sessionId: second } : { name: "result", sessionId: second };
  }
  if (first === "s" && parts.length === 4 && third === "question") {
    return { name: "revise", sessionId: second, questionId: fourth };
  }
  return HOME;
}

/** [순수] 주소를 해시로. */
export function toHash(route: Route): string {
  const e = encodeURIComponent;
  switch (route.name) {
    case "home":
      return "#/";
    case "guide":
      return "#/guide";
    case "request":
    case "mode":
      return `#/${e(route.task)}/${route.name}`;
    case "revise":
      return `#/s/${e(route.sessionId)}/question/${e(route.questionId)}`;
    default:
      return `#/s/${e(route.sessionId)}/${route.name}`;
  }
}

/** [순수] 화면 묶음. 같은 묶음 안에서 옮기면 기다리던 요청을 그대로 받고, 묶음을 떠나면 늦은 응답을 버린다. */
export function contextOf(route: Route): string {
  switch (route.name) {
    case "home":
    case "guide":
      return route.name;
    case "request":
    case "mode":
      return `task:${route.task}`;
    default:
      return `session:${route.sessionId}`;
  }
}

export function taskOf(route: Route): string | null {
  return route.name === "request" || route.name === "mode" ? route.task : null;
}

export function sessionIdOf(route: Route): string | null {
  return "sessionId" in route ? route.sessionId : null;
}
