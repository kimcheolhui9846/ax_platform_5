import { headerSteps } from "../lib/shell";
import type { Phase } from "../lib/shell";

export type HeaderProps = {
  project: string | null;
  phase: Phase | null;
  onPickTask: () => void;
  pickDisabled?: boolean;
};

export function Header({ project, phase, onPickTask, pickDisabled = false }: HeaderProps) {
  const steps = headerSteps(phase);
  return (
    <header className="app-header">
      <div className="header-brand">◈ 창작자 AX</div>
      <div className="header-project">{project ?? "내 창작 작업 공간"}</div>
      <div className="header-steps">
        {steps.length === 0
          ? "하고 싶은 작업 하나부터 시작하세요."
          : steps.map(({ label, current }, i) => (
              <span key={label} className={current ? "header-step is-current" : "header-step"}>
                {`${i + 1} ${label}`}
              </span>
            ))}
      </div>
      <button type="button" className="btn" disabled={pickDisabled} onClick={onPickTask}>
        과제 선택
      </button>
    </header>
  );
}
