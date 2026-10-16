import createClient from "openapi-fetch";
import type { Middleware } from "openapi-fetch";

import { loadClientId, makeClientId } from "../lib/clientId";
import { browserStorage } from "../lib/storage";
import type { paths } from "./schema";

/** API 주소. 버셀에서 백엔드(렌더)를 따로 둘 때 VITE_API_BASE로 바꾼다. 비어 있으면 같은 출처다. */
export function apiBaseUrl(env: string | undefined): string {
  const value = (env ?? "").trim();
  if (!value) return "/";
  return `${value.replace(/\/+$/, "")}/`;
}

export const CLIENT_ID_HEADER = "X-Client-Id";

/** 모든 요청에 익명 사용자 ID를 붙인다. 백엔드는 이 값으로 세션 주인을 가린다(app/api/owner.py). */
export function withClientId(clientId: string): Middleware {
  return {
    onRequest({ request }) {
      request.headers.set(CLIENT_ID_HEADER, clientId);
      return request;
    },
  };
}

export const api = createClient<paths>({ baseUrl: apiBaseUrl(import.meta.env.VITE_API_BASE) });
api.use(withClientId(loadClientId(browserStorage(), makeClientId)));

const FALLBACK_MESSAGE = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.";

export const BACKEND_UNREACHABLE =
  "백엔드가 연결되어 있지 않습니다 — 화면 미리보기는 /preview에서 볼 수 있어요.";

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

/** 우리 백엔드는 실패도 언제나 JSON(ErrorBody)으로 답한다. JSON이 아닌 실패는 버셀 404·프록시·게이트웨이가 낸 것이다. */
function fromBackend(response: Response): boolean {
  return (response.headers.get("content-type") ?? "").includes("application/json");
}

/** 성공 여부는 응답 상태와 오류 유무로 판단한다(본문이 비어 있는 성공도 성공이다). JSON이 아닌 실패는 백엔드 미연결로 본다. */
export function toOutcome<T>({ data, error, response }: ApiResult<T>): Outcome<T> {
  if (response.ok && error === undefined) return { ok: true, data: data as T };
  if (!fromBackend(response)) return { ok: false, message: BACKEND_UNREACHABLE };
  return { ok: false, message: errorMessage(error) };
}
