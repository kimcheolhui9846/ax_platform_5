import type { JSX } from "react";

import type { NavKey, RailItem } from "../lib/shell";
import { DocumentsIcon, HomeIcon, WorkIcon } from "./icons";

export type RailProps = {
  items: RailItem[];
  onNavigate: (key: NavKey) => void;
  onGuide?: () => void;
  guideDisabled?: boolean;
};

const ICONS: Record<NavKey, () => JSX.Element> = { home: HomeIcon, work: WorkIcon, documents: DocumentsIcon };

export function Rail({ items, onNavigate, onGuide, guideDisabled = false }: RailProps) {
  return (
    <nav className="rail" aria-label="주 메뉴">
      <div className="rail-logo">AX</div>
      {items.map(({ key, label, active, disabled }) => {
        const Icon = ICONS[key];
        return (
          <button
            key={key}
            type="button"
            className={active ? "rail-item is-active" : "rail-item"}
            aria-current={active ? "page" : undefined}
            disabled={disabled}
            onClick={() => onNavigate(key)}
          >
            <Icon />
            <span>{label}</span>
          </button>
        );
      })}
      {onGuide && (
        <button type="button" className="rail-help" disabled={guideDisabled} onClick={onGuide}>
          흐름 안내
        </button>
      )}
    </nav>
  );
}
