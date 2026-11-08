import { BACKEND_UNREACHABLE, toOutcome } from "../api/client";
import type { ApiResult } from "../api/client";
import type { InventoryAction, InventoryCall, InventoryForm } from "./state";

/** 요청 하나. done은 성공한 응답을 상태 변경으로 바꾼다. */
export type InventoryRequest<T> = {
  kind: InventoryCall;
  form?: InventoryForm; // 저장 요청을 낸 양식
  request: () => Promise<ApiResult<T>>;
  done: (data: T, seq: number) => InventoryAction;
};

export type InventoryRunner = <T>(call: InventoryRequest<T>) => Promise<void>;

/** 요청마다 번호를 붙여 시작과 끝을 알린다. 번호가 다른(늦게 온) 응답은 리듀서가 버린다. */
export function createInventoryRunner(dispatch: (action: InventoryAction) => void): InventoryRunner {
  let seq = 0;
  return async <T>({ kind, form, request, done }: InventoryRequest<T>) => {
    seq += 1;
    const mine = seq;
    dispatch({ type: "requested", seq: mine, kind, form });
    try {
      const outcome = toOutcome(await request());
      dispatch(outcome.ok ? done(outcome.data, mine) : { type: "failed", seq: mine, message: outcome.message });
    } catch {
      dispatch({ type: "failed", seq: mine, message: BACKEND_UNREACHABLE });
    }
  };
}
