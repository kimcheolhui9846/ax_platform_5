import { useState } from "react";
import type { FormEvent } from "react";

import type { AutoOrderRequest, ItemView } from "../../api/types";
import { DataTable } from "../../components/DataTable";
import type { DataColumn } from "../../components/DataTable";
import { autoFormKey, autoOrderRequest, autoOrderStart } from "../../inventory/forms";
import type { AutoFields } from "../../inventory/forms";
import type { AutoModel, AutoRow } from "../../inventory/orderModel";
import type { InventoryCall } from "../../inventory/state";

export type AutoHandlers = {
  onSaveAutoOrder: (itemId: string, request: AutoOrderRequest) => void;
  onEdited: (form: "auto") => void;
};

type Props = {
  model: AutoModel;
  items: ItemView[];
  saved: number;
  busy: InventoryCall | null;
  on: AutoHandlers;
  /** 처음에 골라 둘 품목(미리보기·테스트용, 없으면 고르지 않음). */
  initialSelected?: string;
};

const CONSENT_TEXT = "부족할 때 하루 마감 직후 이 한도 안에서 자동으로 주문하는 데 동의해요";

/** 편집 카드: 켜기·동의·한도. 판단은 forms.ts의 autoOrderRequest. */
function AutoEditForm({ item, busy, onSave, onEdited }: { item: ItemView; busy: InventoryCall | null; onSave: AutoHandlers["onSaveAutoOrder"]; onEdited: () => void }) {
  const [f, setF] = useState<AutoFields>(() => autoOrderStart(item.auto_order));
  const request = autoOrderRequest(f);
  const set = (patch: Partial<AutoFields>) => {
    setF((current) => ({ ...current, ...patch }));
    onEdited();
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && busy === null) onSave(item.item.item_id, request);
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>{`자동 주문 설정: ${item.item.name}`}</h2>
      <label className="row">
        <input type="checkbox" disabled={busy !== null} checked={f.enabled} onChange={(e) => set({ enabled: e.target.checked })} />
        자동 주문 켜기
      </label>
      {f.enabled && (
        <label className="row">
          <input type="checkbox" disabled={busy !== null} checked={f.consent} onChange={(e) => set({ consent: e.target.checked })} />
          {CONSENT_TEXT}
        </label>
      )}
      <div className="row inv-wrap">
        <input inputMode="decimal" disabled={busy !== null} aria-label="1회 한도(원)" value={f.perOrder} onChange={(e) => set({ perOrder: e.target.value })} />
        <input inputMode="decimal" disabled={busy !== null} aria-label="월 한도(원)" value={f.monthly} onChange={(e) => set({ monthly: e.target.value })} />
      </div>
      <div className="row">
        <button type="submit" className="btn primary" disabled={busy !== null || request === null}>
          {busy === "save" ? "저장 중…" : "저장"}
        </button>
      </div>
    </form>
  );
}

/** S08·S09 자동 주문 탭: 품목별 표와 고른 품목의 편집 카드. */
export function AutoOrderScreen({ model, items, saved, busy, on, initialSelected = "" }: Props) {
  const [selectedId, setSelectedId] = useState(initialSelected);
  const selected = items.find((v) => v.item.item_id === selectedId) ?? null;
  const columns: DataColumn<AutoRow>[] = [
    { key: "name", header: "품목", cell: (r) => r.name },
    { key: "enabled", header: "자동 주문", cell: (r) => (r.enabled ? "켜짐" : "꺼짐") },
    { key: "limits", header: "한도", cell: (r) => r.limitsText },
    { key: "last", header: "최근 결과", cell: (r) => r.lastResult },
    {
      key: "pick",
      header: "설정",
      cell: (r) => (
        <span className="stack">
          <button type="button" className="btn compact" disabled={busy !== null || !r.orderable} onClick={() => setSelectedId(r.itemId)}>
            선택
          </button>
          {!r.orderable && <span className="small muted">{r.reason}</span>}
        </span>
      ),
    },
  ];
  return (
    <div className="stack">
      {model.addressMissing && <p className="notice">배송지를 먼저 설정해 주세요</p>}
      <DataTable caption="자동 주문" columns={columns} rows={model.rows} rowKey={(r) => r.itemId} empty="구매하는 품목이 없어요." />
      {selected !== null && (
        <AutoEditForm
          key={autoFormKey(saved, selected)}
          item={selected}
          busy={busy}
          onSave={on.onSaveAutoOrder}
          onEdited={() => on.onEdited("auto")}
        />
      )}
    </div>
  );
}
