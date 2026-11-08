import { useState } from "react";
import type { FormEvent } from "react";

import type { InventorySettings, InventorySettingsRequest, ItemDraft, ItemKind, ItemPatch, MockOutcome, Procurement, ReorderPolicyRequest, Supplier } from "../../api/types";
import { bulkDrafts, emptyBulkRow, MAX_BULK_ROWS, policyRequest, settingsRequest } from "../../inventory/forms";
import type { BulkRow } from "../../inventory/forms";
import type { ItemRow } from "../../inventory/screenModel";
import { KIND_LABELS, MOCK_OUTCOME_LABELS, PROCUREMENT_LABELS } from "../../lib/inventory/format";

type SavingProps = { saving: boolean }; // 저장 요청 중(그 버튼을 막고 '저장 중…')

function SaveButton({ saving, disabled = false, label = "저장" }: SavingProps & { disabled?: boolean; label?: string }) {
  return (
    <button type="submit" className="btn primary" disabled={saving || disabled}>
      {saving ? "저장 중…" : label}
    </button>
  );
}

function Options<T extends string>({ labels }: { labels: Record<T, string> }) {
  return (
    <>
      {(Object.keys(labels) as T[]).map((k) => (
        <option key={k} value={k}>
          {labels[k]}
        </option>
      ))}
    </>
  );
}

function SupplierSelect({ id, value, suppliers, onChange }: { id: string; value: string; suppliers: Supplier[]; onChange: (id: string) => void }) {
  return (
    <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">거래처 없음</option>
      {suppliers.map((s) => (
        <option key={s.supplier_id} value={s.supplier_id}>
          {s.name}
        </option>
      ))}
    </select>
  );
}

// ---- S01 일괄 등록 ----

export function BulkItemsForm({ suppliers, saving, onCreate, onEdited }: SavingProps & { suppliers: Supplier[]; onCreate: (drafts: ItemDraft[]) => void; onEdited: () => void }) {
  const [rows, setRows] = useState<BulkRow[]>([emptyBulkRow()]);
  const drafts = bulkDrafts(rows);
  const set = (index: number, patch: Partial<BulkRow>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    onEdited();
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (drafts !== null && !saving) onCreate(drafts);
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>품목 일괄 등록</h2>
      <p className="muted">한 줄에 품목 하나. 이름·단위는 꼭 필요하고, 현재 수량을 비우면 미입력이에요. 최대 {MAX_BULK_ROWS}줄.</p>
      {rows.map((row, i) => (
        <div key={i} className="row">
          <input aria-label={`${i + 1}번 이름`} placeholder="이름" value={row.name} onChange={(e) => set(i, { name: e.target.value })} />
          <input aria-label={`${i + 1}번 옵션`} placeholder="옵션" value={row.option} onChange={(e) => set(i, { option: e.target.value })} />
          <select aria-label={`${i + 1}번 종류`} value={row.kind} onChange={(e) => set(i, { kind: e.target.value as ItemKind })}>
            <Options labels={KIND_LABELS} />
          </select>
          <input aria-label={`${i + 1}번 단위`} placeholder="단위" value={row.unit} onChange={(e) => set(i, { unit: e.target.value })} />
          <select aria-label={`${i + 1}번 조달`} value={row.procurement} onChange={(e) => set(i, { procurement: e.target.value as Procurement })}>
            <Options labels={PROCUREMENT_LABELS} />
          </select>
          <select aria-label={`${i + 1}번 거래처`} value={row.supplierId} onChange={(e) => set(i, { supplierId: e.target.value })}>
            <option value="">거래처 없음</option>
            {suppliers.map((s) => (
              <option key={s.supplier_id} value={s.supplier_id}>
                {s.name}
              </option>
            ))}
          </select>
          <input aria-label={`${i + 1}번 현재 수량`} inputMode="decimal" placeholder="현재 수량" value={row.quantity} onChange={(e) => set(i, { quantity: e.target.value })} />
          <button type="button" className="btn compact" disabled={rows.length === 1} onClick={() => setRows((c) => c.filter((_, k) => k !== i))}>
            {i + 1}번 줄 빼기
          </button>
        </div>
      ))}
      <div className="row">
        <button type="button" className="btn" disabled={rows.length >= MAX_BULK_ROWS} onClick={() => setRows((c) => [...c, emptyBulkRow()])}>
          줄 추가
        </button>
        <button type="submit" className="btn primary" disabled={saving || drafts === null}>
          {saving ? "저장 중…" : "등록"}
        </button>
      </div>
    </form>
  );
}

// ---- S02 품목 편집 ----

export function ItemEditForm({ item, suppliers, saving, onSave, onEdited }: SavingProps & { item: ItemRow; suppliers: Supplier[]; onSave: (itemId: string, patch: ItemPatch) => void; onEdited: () => void }) {
  const [f, setF] = useState({ name: item.name, option: item.option, kind: item.kind, unit: item.unit, procurement: item.procurement, supplierId: item.supplierId });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const valid = f.name.trim() !== "" && f.unit.trim() !== "";
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!valid || saving) return;
    onSave(item.itemId, {
      name: f.name.trim(),
      option: f.option.trim() === "" ? null : f.option.trim(),
      kind: f.kind,
      unit: f.unit.trim(),
      procurement: f.procurement,
      supplier_id: f.supplierId === "" ? null : f.supplierId,
    });
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>품목 편집: {item.name}</h2>
      <div className="field-row">
        <label htmlFor="edit-name">이름</label>
        <input id="edit-name" value={f.name} onChange={(e) => set({ name: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor="edit-option">옵션</label>
        <input id="edit-option" value={f.option} onChange={(e) => set({ option: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor="edit-kind">종류</label>
        <select id="edit-kind" value={f.kind} onChange={(e) => set({ kind: e.target.value as ItemKind })}>
          <Options labels={KIND_LABELS} />
        </select>
      </div>
      <div className="field-row">
        <label htmlFor="edit-unit">단위</label>
        <input id="edit-unit" value={f.unit} onChange={(e) => set({ unit: e.target.value })} />
        <p className="small muted">수량 기록이 있는 품목은 단위를 바꿀 수 없어요.</p>
      </div>
      <div className="field-row">
        <label htmlFor="edit-procurement">조달</label>
        <select id="edit-procurement" value={f.procurement} onChange={(e) => set({ procurement: e.target.value as Procurement })}>
          <Options labels={PROCUREMENT_LABELS} />
        </select>
      </div>
      <div className="field-row">
        <label htmlFor="edit-supplier">거래처</label>
        <SupplierSelect id="edit-supplier" value={f.supplierId} suppliers={suppliers} onChange={(supplierId) => set({ supplierId })} />
      </div>
      <div className="row">
        <SaveButton saving={saving} disabled={!valid} />
        <button type="button" className="btn" disabled={saving} onClick={() => onSave(item.itemId, { archived: true })}>
          숨기기
        </button>
      </div>
    </form>
  );
}

// ---- 거래처 ----

function SupplierRow({ supplier, saving, onSave }: SavingProps & { supplier: Supplier; onSave: (id: string, patch: { name?: string; mock_outcome?: MockOutcome }) => void }) {
  const [name, setName] = useState(supplier.name);
  const [outcome, setOutcome] = useState<MockOutcome>(supplier.mock_outcome);
  const changed = name.trim() !== supplier.name || outcome !== supplier.mock_outcome;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (changed && name.trim() !== "" && !saving) onSave(supplier.supplier_id, { name: name.trim(), mock_outcome: outcome });
  };
  return (
    <form className="row" onSubmit={submit}>
      <input aria-label={`${supplier.name} 이름`} value={name} onChange={(e) => setName(e.target.value)} />
      <select aria-label={`${supplier.name} 모의 거래처 응답`} value={outcome} onChange={(e) => setOutcome(e.target.value as MockOutcome)}>
        <Options labels={MOCK_OUTCOME_LABELS} />
      </select>
      <SaveButton saving={saving} disabled={!changed || name.trim() === ""} />
    </form>
  );
}

export function SuppliersSection({
  suppliers,
  saving,
  onCreate,
  onUpdate,
}: SavingProps & {
  suppliers: Supplier[];
  onCreate: (draft: { name: string; mock_outcome: MockOutcome }) => void;
  onUpdate: (id: string, patch: { name?: string; mock_outcome?: MockOutcome }) => void;
}) {
  const [name, setName] = useState("");
  const [outcome, setOutcome] = useState<MockOutcome>("accept");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() === "" || saving) return;
    onCreate({ name: name.trim(), mock_outcome: outcome });
    setName("");
  };
  return (
    <section className="card stack" aria-label="거래처">
      <h2>거래처</h2>
      {suppliers.length === 0 && <p className="muted">등록한 거래처가 없어요.</p>}
      {suppliers.map((s) => (
        <SupplierRow key={`${s.supplier_id}:${s.name}:${s.mock_outcome}`} supplier={s} saving={saving} onSave={onUpdate} />
      ))}
      <form className="row" onSubmit={submit}>
        <input aria-label="새 거래처 이름" placeholder="새 거래처 이름" value={name} onChange={(e) => setName(e.target.value)} />
        <select aria-label="새 거래처 모의 거래처 응답" value={outcome} onChange={(e) => setOutcome(e.target.value as MockOutcome)}>
          <Options labels={MOCK_OUTCOME_LABELS} />
        </select>
        <SaveButton saving={saving} disabled={name.trim() === ""} label="거래처 추가" />
      </form>
    </section>
  );
}

// ---- S03 보충 기준 ----

export function PolicyForm({
  item,
  saving,
  suggesting,
  onSave,
  onSuggest,
  onApply,
  onEdited,
}: SavingProps & {
  item: ItemRow;
  suggesting: boolean;
  onSave: (itemId: string, request: ReorderPolicyRequest) => void;
  onSuggest: (itemId: string) => void;
  onApply: (itemId: string) => void;
  onEdited: () => void;
}) {
  const p = item.policy;
  const [f, setF] = useState({ min: p?.min_stock ?? "", target: p?.target_stock ?? "", unit: p?.purchase_unit ?? "", lead: p === null ? "" : String(p.lead_days), price: p?.unit_price ?? "" });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const request = policyRequest(f);
  const busy = saving || suggesting;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && !busy) onSave(item.itemId, request);
  };
  const field = (id: string, label: string, key: keyof typeof f) => (
    <div className="field-row">
      <label htmlFor={`policy-${id}`}>{label}</label>
      <input id={`policy-${id}`} inputMode="decimal" value={f[key]} onChange={(e) => set({ [key]: e.target.value })} />
    </div>
  );
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>보충 기준: {item.name}</h2>
      {field("min", `최소 재고(${item.unit})`, "min")}
      {field("target", `목표 재고(${item.unit})`, "target")}
      {field("unit", `구매 단위(${item.unit})`, "unit")}
      {field("lead", "배송 기간(일)", "lead")}
      {field("price", "단가(원)", "price")}
      <div className="row">
        <SaveButton saving={saving} disabled={request === null || suggesting} />
        <button type="button" className="btn" disabled={busy} onClick={() => onSuggest(item.itemId)}>
          {suggesting ? "추천 받는 중…" : "AI 추천 받기"}
        </button>
      </div>
      {item.suggestion !== null && (
        <div className="notice stack8">
          <p>
            <span className="inv-badge">{item.suggestion.label}</span> {item.suggestion.text}
          </p>
          <p className="muted">{item.suggestion.reason}</p>
          <button type="button" className="btn compact" disabled={busy} onClick={() => onApply(item.itemId)}>
            추천 적용
          </button>
        </div>
      )}
    </form>
  );
}

// ---- 설정 ----

export function SettingsForm({ settings, saving, onSave, onEdited }: SavingProps & { settings: InventorySettings; onSave: (request: InventorySettingsRequest) => void; onEdited: () => void }) {
  const [f, setF] = useState({ address: settings.address, ratio: settings.anomaly_drop_ratio, staleDays: String(settings.stale_days) });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const request = settingsRequest(f);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && !saving) onSave(request);
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>설정</h2>
      <div className="field-row">
        <label htmlFor="set-address">배송지</label>
        <input id="set-address" value={f.address} onChange={(e) => set({ address: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor="set-ratio">이상 수량 비율</label>
        <input id="set-ratio" inputMode="decimal" value={f.ratio} onChange={(e) => set({ ratio: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor="set-stale">오래된 실사 일수</label>
        <input id="set-stale" inputMode="numeric" value={f.staleDays} onChange={(e) => set({ staleDays: e.target.value })} />
      </div>
      <SaveButton saving={saving} disabled={request === null} />
    </form>
  );
}
