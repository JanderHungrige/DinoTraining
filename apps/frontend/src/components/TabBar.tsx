/**
 * Top-level tab strip.
 *
 * Implements the WAI-ARIA tabs pattern: a roving tabindex (only the active tab is
 * in the tab order), arrow keys to move between tabs, Home/End to jump. Real
 * `<button>` elements, so Enter/Space and focus rings come for free.
 */

import { useRef, type JSX, type KeyboardEvent } from 'react';

import { useT } from '../i18n';
import { TABS, tabLabel, type TabId } from '../tabs/tabs';

export interface TabBarProps {
  readonly activeTab: TabId;
  readonly onTabChange: (tab: TabId) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps): JSX.Element {
  const { t } = useT();
  const tabRefs = useRef<Map<TabId, HTMLButtonElement>>(new Map());

  const focusTab = (id: TabId): void => {
    onTabChange(id);
    tabRefs.current.get(id)?.focus();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>): void => {
    const currentIndex = TABS.findIndex((tab) => tab.id === activeTab);
    if (currentIndex === -1) return;

    const lastIndex = TABS.length - 1;
    let nextIndex: number | null = null;

    switch (event.key) {
      case 'ArrowRight':
        nextIndex = currentIndex === lastIndex ? 0 : currentIndex + 1;
        break;
      case 'ArrowLeft':
        nextIndex = currentIndex === 0 ? lastIndex : currentIndex - 1;
        break;
      case 'Home':
        nextIndex = 0;
        break;
      case 'End':
        nextIndex = lastIndex;
        break;
      default:
        return;
    }

    const next = TABS[nextIndex];
    if (!next) return;
    event.preventDefault();
    focusTab(next.id);
  };

  return (
    <div className="tabbar" role="tablist" aria-label={t('app.tabs.sections')}>
      {TABS.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            ref={(node) => {
              if (node) tabRefs.current.set(tab.id, node);
              else tabRefs.current.delete(tab.id);
            }}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            className={isActive ? 'tabbar__tab tabbar__tab--active' : 'tabbar__tab'}
            aria-selected={isActive}
            aria-controls={`panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={handleKeyDown}
          >
            {tabLabel(t, tab.id)}
          </button>
        );
      })}
    </div>
  );
}
