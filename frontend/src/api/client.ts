import createClient from "openapi-fetch";

import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: "/" });

const FALLBACK_MESSAGE = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";

/**
 * openapi-fetch 응답 중 화면이 쓰는 부분. 백엔드 오류 본문은 계약상 ErrorBody({detail})지만
 * 개발 프록시·게이트웨이 오류처럼 계약 밖 본문도 올 수 있어 error는 unknown으로 받고 errorMessage가 거른다.
 */
export type ApiResult<T> = { data?: T; error?: unknown; response: Response };

export type Outcome<T> = { ok: true; data: T } | { ok: false; message: string };

/** 런타임 오류 본문은 항상 {detail: 한글 문자열}이다. 그 외 모양은 기본 문구로 대신한다. */
export function errorMessage(error: unknown): string {
  if (error && typeof error === "object" && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return FALLBACK_MESSAGE;
}

/** 성공 여부는 응답 상태와 오류 유무로 판단한다(본문이 비어 있는 성공도 성공이다). */
export function toOutcome<T>({ data, error, response }: ApiResult<T>): Outcome<T> {
  if (response.ok && error === undefined) return { ok: true, data: data as T };
  return { ok: false, message: errorMessage(error) };
}
