/**
 * Placeholder body for a tab whose feature has not landed yet.
 *
 * Deliberately states which wave fills it in — an empty panel reads as a bug,
 * a panel that says "Wave 3" reads as a plan.
 */

import type { JSX } from 'react';

import { getTab, type TabId } from '../tabs/tabs';

export interface StubPanelProps {
  readonly tabId: TabId;
}

export function StubPanel({ tabId }: StubPanelProps): JSX.Element {
  const tab = getTab(tabId);
  return (
    <section className="stub">
      <h2 className="stub__title">{tab.label}</h2>
      <p className="stub__hint">{tab.hint}</p>
      <p className="stub__wave">Arrives in Wave {tab.wave}.</p>
    </section>
  );
}
