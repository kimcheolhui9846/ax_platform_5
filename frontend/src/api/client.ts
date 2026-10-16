import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "/" });

const FALLBACK_MESSAGE = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";

/** 런타임 오류 본문은 항상 {detail: 한글 문자열}이다. 그 외 모양은 기본 문구로 대신한다. */
export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return FALLBACK_MESSAGE;
}
