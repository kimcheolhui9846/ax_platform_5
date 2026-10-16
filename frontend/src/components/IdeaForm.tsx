type Props = {
  title: string;
  value: string;
  busy: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function IdeaForm({ title, value, busy, onChange, onSubmit }: Props) {
  return (
    <section className="card">
      <h2>{title}</h2>
      <p className="hint">아이디어를 한 줄로 적어 주세요.</p>
      <textarea value={value} onChange={(e) => onChange(e.target.value)} rows={3} />
      <button type="button" disabled={busy || !value.trim()} onClick={onSubmit}>
        시작하기
      </button>
    </section>
  );
}
