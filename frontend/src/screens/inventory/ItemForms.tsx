import { useId, useState } from "react";
import type { FormEvent } from "react";

import type { InventorySettings, InventorySettingsRequest, ItemDraft, ItemKind, ItemPatch, MockOutcome, Procurement, ReorderPolicyRequest, Supplier } from "../../api/types";
import { bulkDrafts, emptyBulkRow, MAX_BULK_ROWS, policyRequest, settingsRequest } from "../../inventory/forms";
import type { BulkRow } from "../../inventory/forms";
import type { InventoryCall } from "../../inventory/state";
import type { ItemRow } from "../../inventory/screenModel";
import { KIND_LABELS, MOCK_OUTCOME_LABELS, PROCUREMENT_LABELS } from "../../lib/inventory/format";

type BusyProps = { busy: InventoryCall | null }; // 요청 중이면 모든 입력·버튼을 막고, 눌린 버튼에만 진행 글

function SaveButton({ busy, disabled = false, label = "저장" }: BusyProps & { disabled?: boolean; label?: string }) {
  return (
    <button type="submit" className="btn primary" disabled={busy !== null || disabled}>
      {busy === "save" ? "저장 중…" : label}
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

function SupplierSelect({ id, value, suppliers, disabled, onChange }: { id: string; value: string; suppliers: Supplier[]; disabled: boolean; onChange: (id: string) => void }) {
  return (
    <select id={id} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)}>
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

export function BulkItemsForm({ suppliers, busy, onCreate, onEdited }: BusyProps & { suppliers: Supplier[]; onCreate: (drafts: ItemDraft[]) => void; onEdited: () => void }) {
  const [rows, setRows] = useState<BulkRow[]>([emptyBulkRow()]);
  const drafts = bulkDrafts(rows);
  const set = (index: number, patch: Partial<BulkRow>) => {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    onEdited();
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (drafts !== null && busy === null) onCreate(drafts);
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>품목 일괄 등록</h2>
      <p className="muted">한 줄에 품목 하나. 이름·단위는 꼭 필요하고, 현재 수량을 비우면 미입력이에요. 최대 {MAX_BULK_ROWS}줄.</p>
      {rows.map((row, i) => (
        <div key={i} className="inv-bulk-row">
          <input disabled={busy !== null} aria-label={`${i + 1}번 이름`} placeholder="이름" value={row.name} onChange={(e) => set(i, { name: e.target.value })} />
          <input disabled={busy !== null} aria-label={`${i + 1}번 옵션`} placeholder="옵션" value={row.option} onChange={(e) => set(i, { option: e.target.value })} />
          <select disabled={busy !== null} aria-label={`${i + 1}번 종류`} value={row.kind} onChange={(e) => set(i, { kind: e.target.value as ItemKind })}>
            <Options labels={KIND_LABELS} />
          </select>
          <input disabled={busy !== null} aria-label={`${i + 1}번 단위`} placeholder="단위" value={row.unit} onChange={(e) => set(i, { unit: e.target.value })} />
          <select disabled={busy !== null} aria-label={`${i + 1}번 조달`} value={row.procurement} onChange={(e) => set(i, { procurement: e.target.value as Procurement })}>
            <Options labels={PROCUREMENT_LABELS} />
          </select>
          <select disabled={busy !== null} aria-label={`${i + 1}번 거래처`} value={row.supplierId} onChange={(e) => set(i, { supplierId: e.target.value })}>
            <option value="">거래처 없음</option>
            {suppliers.map((s) => (
              <option key={s.supplier_id} value={s.supplier_id}>
                {s.name}
              </option>
            ))}
          </select>
          <input disabled={busy !== null} aria-label={`${i + 1}번 현재 수량`} inputMode="decimal" placeholder="현재 수량" value={row.quantity} onChange={(e) => set(i, { quantity: e.target.value })} />
          <button type="button" className="btn compact" disabled={busy !== null || rows.length === 1} onClick={() => { setRows((c) => c.filter((_, k) => k !== i)); onEdited(); }}>
            {i + 1}번 줄 빼기
          </button>
        </div>
      ))}
      <div className="row">
        <button type="button" className="btn" disabled={busy !== null || rows.length >= MAX_BULK_ROWS} onClick={() => { setRows((c) => [...c, emptyBulkRow()]); onEdited(); }}>
          줄 추가
        </button>
        <button type="submit" className="btn primary" disabled={busy !== null || drafts === null}>
          {busy === "save" ? "저장 중…" : "등록"}
        </button>
      </div>
    </form>
  );
}

// ---- S02 품목 편집 ----

export function ItemEditForm({ item, suppliers, busy, onSave, onEdited }: BusyProps & { item: ItemRow; suppliers: Supplier[]; onSave: (itemId: string, patch: ItemPatch) => void; onEdited: () => void }) {
  const uid = useId();
  const [f, setF] = useState({ name: item.name, option: item.option, kind: item.kind, unit: item.unit, procurement: item.procurement, supplierId: item.supplierId });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const valid = f.name.trim() !== "" && f.unit.trim() !== "";
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!valid || busy !== null) return;
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
        <label htmlFor={`${uid}-edit-name`}>이름</label>
        <input disabled={busy !== null} id={`${uid}-edit-name`} value={f.name} onChange={(e) => set({ name: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-edit-option`}>옵션</label>
        <input disabled={busy !== null} id={`${uid}-edit-option`} value={f.option} onChange={(e) => set({ option: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-edit-kind`}>종류</label>
        <select disabled={busy !== null} id={`${uid}-edit-kind`} value={f.kind} onChange={(e) => set({ kind: e.target.value as ItemKind })}>
          <Options labels={KIND_LABELS} />
        </select>
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-edit-unit`}>단위</label>
        <input disabled={busy !== null || item.counted} id={`${uid}-edit-unit`} value={f.unit} onChange={(e) => set({ unit: e.target.value })} />
        {item.counted && <p className="small muted">수량 기록이 있는 품목은 단위를 바꿀 수 없어요.</p>}
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-edit-procurement`}>조달</label>
        <select disabled={busy !== null} id={`${uid}-edit-procurement`} value={f.procurement} onChange={(e) => set({ procurement: e.target.value as Procurement })}>
          <Options labels={PROCUREMENT_LABELS} />
        </select>
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-edit-supplier`}>거래처</label>
        <SupplierSelect id={`${uid}-edit-supplier`} value={f.supplierId} suppliers={suppliers} disabled={busy !== null} onChange={(supplierId) => set({ supplierId })} />
      </div>
      <div className="row">
        <SaveButton busy={busy} disabled={!valid} />
        <button type="button" className="btn" disabled={busy !== null} onClick={() => onSave(item.itemId, { archived: true })}>
          숨기기
        </button>
      </div>
    </form>
  );
}

// ---- 거래처 ----

function SupplierRow({ supplier, busy, onSave, onEdited }: BusyProps & { supplier: Supplier; onSave: (id: string, patch: { name?: string; mock_outcome?: MockOutcome }) => void; onEdited: () => void }) {
  const [name, setName] = useState(supplier.name);
  const [outcome, setOutcome] = useState<MockOutcome>(supplier.mock_outcome);
  const changed = name.trim() !== supplier.name || outcome !== supplier.mock_outcome;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (changed && name.trim() !== "" && busy === null) onSave(supplier.supplier_id, { name: name.trim(), mock_outcome: outcome });
  };
  return (
    <form className="row inv-wrap" onSubmit={submit}>
      <input disabled={busy !== null} aria-label={`${supplier.name} 이름`} value={name} onChange={(e) => { setName(e.target.value); onEdited(); }} />
      <select disabled={busy !== null} aria-label={`${supplier.name} 모의 거래처 응답`} value={outcome} onChange={(e) => { setOutcome(e.target.value as MockOutcome); onEdited(); }}>
        <Options labels={MOCK_OUTCOME_LABELS} />
      </select>
      <SaveButton busy={busy} disabled={!changed || name.trim() === ""} />
    </form>
  );
}

export function SuppliersSection({
  suppliers,
  busy,
  onCreate,
  onUpdate,
  onEdited,
}: BusyProps & {
  suppliers: Supplier[];
  onCreate: (draft: { name: string; mock_outcome: MockOutcome }) => void;
  onUpdate: (id: string, patch: { name?: string; mock_outcome?: MockOutcome }) => void;
  onEdited: () => void;
}) {
  const [name, setName] = useState("");
  const [outcome, setOutcome] = useState<MockOutcome>("accept");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (name.trim() === "" || busy !== null) return;
    onCreate({ name: name.trim(), mock_outcome: outcome });
  };
  return (
    <section className="card stack" aria-label="거래처">
      <h2>거래처</h2>
      {suppliers.length === 0 && <p className="muted">등록한 거래처가 없어요.</p>}
      {suppliers.map((s) => (
        <SupplierRow key={`${s.supplier_id}:${s.name}:${s.mock_outcome}`} supplier={s} busy={busy} onSave={onUpdate} onEdited={onEdited} />
      ))}
      <form className="row inv-wrap" onSubmit={submit}>
        <input disabled={busy !== null} aria-label="새 거래처 이름" placeholder="새 거래처 이름" value={name} onChange={(e) => { setName(e.target.value); onEdited(); }} />
        <select disabled={busy !== null} aria-label="새 거래처 모의 거래처 응답" value={outcome} onChange={(e) => { setOutcome(e.target.value as MockOutcome); onEdited(); }}>
          <Options labels={MOCK_OUTCOME_LABELS} />
        </select>
        <SaveButton busy={busy} disabled={name.trim() === ""} label="거래처 추가" />
      </form>
    </section>
  );
}

// ---- S03 보충 기준 ----

export function PolicyForm({
  item,
  busy,
  onSave,
  onSuggest,
  onApply,
  onEdited,
}: BusyProps & {
  item: ItemRow;
  onSave: (itemId: string, request: ReorderPolicyRequest) => void;
  onSuggest: (itemId: string) => void;
  onApply: (itemId: string) => void;
  onEdited: () => void;
}) {
  const uid = useId();
  const p = item.policy;
  const [f, setF] = useState({ min: p?.min_stock ?? "", target: p?.target_stock ?? "", unit: p?.purchase_unit ?? "", lead: p === null ? "" : String(p.lead_days), price: p?.unit_price ?? "" });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const request = policyRequest(f);
  const working = busy !== null;
  const suggesting = busy === "suggest";
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && !busy) onSave(item.itemId, request);
  };
  const field = (id: string, label: string, key: keyof typeof f) => (
    <div className="field-row">
      <label htmlFor={`${uid}-policy-${id}`}>{label}</label>
      <input disabled={busy !== null} id={`${uid}-policy-${id}`} inputMode="decimal" value={f[key]} onChange={(e) => set({ [key]: e.target.value })} />
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
        <SaveButton busy={busy} disabled={request === null} />
        <button type="button" className="btn" disabled={working || p === null} onClick={() => onSuggest(item.itemId)}>
          {suggesting ? "추천 받는 중…" : "AI 추천 받기"}
        </button>
      </div>
      {p === null && <p className="small muted">보충 기준을 저장하면 AI 추천을 받을 수 있어요.</p>}
      {item.suggestion !== null && (
        <div className="notice stack8">
          <p>
            <span className="inv-badge">{item.suggestion.label}</span> {item.suggestion.text}
          </p>
          <p className="muted">{item.suggestion.reason}</p>
          <button type="button" className="btn compact" disabled={working} onClick={() => onApply(item.itemId)}>
            추천 적용
          </button>
        </div>
      )}
    </form>
  );
}

// ---- 설정 ----

export function SettingsForm({ settings, busy, onSave, onEdited }: BusyProps & { settings: InventorySettings; onSave: (request: InventorySettingsRequest) => void; onEdited: () => void }) {
  const uid = useId();
  const [f, setF] = useState({ address: settings.address, ratio: settings.anomaly_drop_ratio, staleDays: String(settings.stale_days) });
  const set = (patch: Partial<typeof f>) => {
    setF((c) => ({ ...c, ...patch }));
    onEdited();
  };
  const request = settingsRequest(f);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (request !== null && busy === null) onSave(request);
  };
  return (
    <form className="card stack" onSubmit={submit}>
      <h2>설정</h2>
      <div className="field-row">
        <label htmlFor={`${uid}-set-address`}>배송지</label>
        <input disabled={busy !== null} id={`${uid}-set-address`} value={f.address} onChange={(e) => set({ address: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-set-ratio`}>이상 수량 비율</label>
        <input disabled={busy !== null} id={`${uid}-set-ratio`} inputMode="decimal" value={f.ratio} onChange={(e) => set({ ratio: e.target.value })} />
      </div>
      <div className="field-row">
        <label htmlFor={`${uid}-set-stale`}>오래된 실사 일수</label>
        <input disabled={busy !== null} id={`${uid}-set-stale`} inputMode="numeric" value={f.staleDays} onChange={(e) => set({ staleDays: e.target.value })} />
      </div>
      <SaveButton busy={busy} disabled={request === null} />
    </form>
  );
}
