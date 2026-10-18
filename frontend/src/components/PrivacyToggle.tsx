type Props = {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
};

/** 'AI에 보내지 않기' 체크 칸. 값은 부모가 가진다. */
export function PrivacyToggle({ label, checked, disabled = false, onChange }: Props) {
  return (
    <label className="privacy-toggle">
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}
