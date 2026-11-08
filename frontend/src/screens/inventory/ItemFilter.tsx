import { useId } from "react";

import type { ItemKind } from "../../api/types";
import { KIND_LABELS } from "../../lib/inventory/format";

export type FilterChange = { query?: string; kind?: ItemKind | "all" };

type Props = {
  query: string;
  kind: ItemKind | "all";
  disabled?: boolean;
  onChange: (filter: FilterChange) => void;
};

/** 현황·마감이 같이 쓰는 검색 칸과 분류 선택. */
export function ItemFilter({ query, kind, disabled = false, onChange }: Props) {
  const uid = useId();
  return (
    <div className="row inv-filter">
      <label htmlFor={`${uid}-query`} className="small">
        품목 검색
      </label>
      <input
        id={`${uid}-query`}
        type="search"
        value={query}
        disabled={disabled}
        placeholder="이름·옵션"
        onChange={(event) => onChange({ query: event.target.value })}
      />
      <label htmlFor={`${uid}-kind`} className="small">
        분류
      </label>
      <select
        id={`${uid}-kind`}
        value={kind}
        disabled={disabled}
        onChange={(event) => onChange({ kind: event.target.value as ItemKind | "all" })}
      >
        <option value="all">전체</option>
        {(Object.keys(KIND_LABELS) as ItemKind[]).map((k) => (
          <option key={k} value={k}>
            {KIND_LABELS[k]}
          </option>
        ))}
      </select>
    </div>
  );
}
