import { useId } from "react";

type Props = {
  label: string;
  value: string;
  placeholder: string;
  rows: number;
  maxLength: number;
  submitLabel: string;
  busy: boolean;
  canSubmit?: boolean; // 글 말고 보낼 수 있는 다른 조건(예: 지금 글과 다르다). 기본은 보낼 수 있다
  onChange: (text: string) => void;
  onSubmit: (text: string) => void;
};

/** 글 입력과 보내기. 값은 부모가 가진다. 보낼 때는 앞뒤 공백을 지운 글을 넘긴다. */
export function Composer({ label, value, placeholder, rows, maxLength, submitLabel, busy, canSubmit = true, onChange, onSubmit }: Props) {
  const id = useId();
  const text = value.trim();
  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault();
        if (text && canSubmit && !busy) onSubmit(text);
      }}
    >
      <label htmlFor={id} className="small muted">
        {label}
      </label>
      <textarea
        id={id}
        rows={rows}
        maxLength={maxLength}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="row">
        <span className="muted grow">짧게 적어도 괜찮아요.</span>
        <button type="submit" className="btn primary send" disabled={busy || !text || !canSubmit}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
