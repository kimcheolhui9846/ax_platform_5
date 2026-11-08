import { useId, useState } from "react";

import type { InventorySettingsRequest, ItemDraft, ItemPatch, MockOutcome, ReorderPolicyRequest } from "../../api/types";
import type { ItemsModel } from "../../inventory/screenModel";
import type { InventoryCall, InventoryForm } from "../../inventory/state";
import { BulkItemsForm, ItemEditForm, PolicyForm, SettingsForm, SuppliersSection } from "./ItemForms";

export type ItemsHandlers = {
  onCreateItems: (drafts: ItemDraft[]) => void;
  onUpdateItem: (itemId: string, patch: ItemPatch) => void;
  onCreateSupplier: (draft: { name: string; mock_outcome: MockOutcome }) => void;
  onUpdateSupplier: (id: string, patch: { name?: string; mock_outcome?: MockOutcome }) => void;
  onSavePolicy: (itemId: string, request: ReorderPolicyRequest) => void;
  onSuggest: (itemId: string) => void;
  onApplySuggestion: (itemId: string) => void;
  onSaveSettings: (request: InventorySettingsRequest) => void;
  /** 그 양식에 저장하지 않은 입력이 생겼다(탭을 옮길 때 확인하려고). */
  onEdited: (form: InventoryForm) => void;
};

type Props = { model: ItemsModel; busy: InventoryCall | null; on: ItemsHandlers };

/** 품목·기준 탭: 일괄 등록, 품목 편집, 거래처, 보충 기준, 설정. 저장이 성공해 새 값이 오면 양식은 그 값으로 다시 시작한다(key). */
export function ItemsScreen({ model, busy, on }: Props) {
  const uid = useId();
  const [selectedId, setSelectedId] = useState("");
  const selected = model.rows.find((r) => r.itemId === selectedId) ?? null;
  return (
    <div className="stack">
      <BulkItemsForm key={`bulk:${model.saved.bulk}`} suppliers={model.suppliers} busy={busy} onCreate={on.onCreateItems} onEdited={() => on.onEdited("bulk")} />
      <section className="card stack" aria-label="품목 선택">
        <h2>품목 편집·보충 기준</h2>
        {model.rows.length === 0 ? (
          <p className="muted">등록한 품목이 없어요.</p>
        ) : (
          <div className="field-row">
            <label htmlFor={`${uid}-pick`}>품목 선택</label>
            <select id={`${uid}-pick`} disabled={busy !== null} value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
              <option value="">선택해 주세요</option>
              {model.rows.map((r) => (
                <option key={r.itemId} value={r.itemId}>
                  {r.name}
                  {r.option !== "" && ` (${r.option})`} · {r.policyText}
                </option>
              ))}
            </select>
          </div>
        )}
      </section>
      {selected !== null && (
        <>
          <ItemEditForm
            key={`edit:${model.saved.item}:${selected.itemId}:${selected.name}:${selected.option}:${selected.kind}:${selected.unit}:${selected.procurement}:${selected.supplierId}`}
            item={selected}
            suppliers={model.suppliers}
            busy={busy}
            onSave={on.onUpdateItem}
            onEdited={() => on.onEdited("item")}
          />
          <PolicyForm
            key={`policy:${model.saved.policy}:${selected.itemId}:${selected.policyText}`}
            item={selected}
            busy={busy}
            onSave={on.onSavePolicy}
            onSuggest={on.onSuggest}
            onApply={on.onApplySuggestion}
            onEdited={() => on.onEdited("policy")}
          />
        </>
      )}
      <SuppliersSection
        key={`suppliers:${model.saved.supplier}`}
        suppliers={model.suppliers}
        busy={busy}
        onCreate={on.onCreateSupplier}
        onUpdate={on.onUpdateSupplier}
        onEdited={() => on.onEdited("supplier")}
      />
      <SettingsForm
        key={`settings:${model.saved.settings}:${model.settings.address}:${model.settings.anomaly_drop_ratio}:${model.settings.stale_days}`}
        settings={model.settings}
        busy={busy}
        onSave={on.onSaveSettings}
        onEdited={() => on.onEdited("settings")}
      />
    </div>
  );
}
