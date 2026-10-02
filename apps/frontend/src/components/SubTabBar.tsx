/**
 * A row of sub-tabs inside a tab (doc 135), with the same keyboard pattern as the main
 * TabBar: a roving tabindex, arrow keys, Home/End, real buttons.
 */

import { useRef, type JSX, type KeyboardEvent } from 'react';

export interface SubTab<T extends string> {
  readonly id: T;
  readonly label: string;
}

interface SubTabBarProps<T extends string> {
  readonly tabs: readonly SubTab<T>[];
  readonly active: T;
  readonly onChange: (id: T) => void;
  readonly label: string;
  /** Prefix for the ids that tie each tab to its panel (`${idPrefix}-tab-${id}`). */
  readonly idPrefix: string;
}

export function SubTabBar<T extends string>({ tabs, active, onChange, label, idPrefix }: SubTabBarProps<T>): JSX.Element {
  const refs = useRef<Map<T, HTMLButtonElement>>(new Map());

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>): void => {
    const index = tabs.findIndex((tab) => tab.id === active);
    const last = tabs.length - 1;
    const next =
      event.key === 'ArrowRight' ? (index === last ? 0 : index + 1)
      : event.key === 'ArrowLeft' ? (index === 0 ? last : index - 1)
      : event.key === 'Home' ? 0
      : event.key === 'End' ? last
      : null;
    const target = next === null ? undefined : tabs[next];
    if (!target) return;
    event.preventDefault();
    onChange(target.id);
    refs.current.get(target.id)?.focus();
  };

  return (
    <div className="subtabs" role="tablist" aria-label={label}>
      {tabs.map((tab) => {
        const selected = tab.id === active;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              if (node) refs.current.set(tab.id, node);
              else refs.current.delete(tab.id);
            }}
            type="button"
            role="tab"
            id={`${idPrefix}-tab-${tab.id}`}
            aria-selected={selected}
            aria-controls={`${idPrefix}-panel-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            className={selected ? 'subtabs__tab subtabs__tab--active' : 'subtabs__tab'}
            onClick={() => onChange(tab.id)}
            onKeyDown={onKeyDown}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
