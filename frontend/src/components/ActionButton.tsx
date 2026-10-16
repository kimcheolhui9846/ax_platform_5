import { actionButton } from "../lib/screen";
import type { SessionAction } from "../lib/screen";

type Props = {
  action: SessionAction;
  className: string;
  state: { busy: boolean; canGenerate: boolean };
  onAct: (action: SessionAction) => void;
};

export function ActionButton({ action, className, state, onAct }: Props) {
  const { label, disabled } = actionButton(action, state);
  return (
    <button type="button" className={className} disabled={disabled} onClick={() => onAct(action)}>
      {label}
    </button>
  );
}
