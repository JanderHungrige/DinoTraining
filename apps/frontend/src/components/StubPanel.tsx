/**
 * Placeholder body for a tab whose feature has not landed yet.
 *
 * Deliberately states which wave fills it in — an empty panel reads as a bug,
 * a panel that says "Wave 3" reads as a plan.
 */

import type { JSX } from 'react';

import { useT } from '../i18n';
import { getTab, tabHint, tabLabel, type TabId } from '../tabs/tabs';

export interface StubPanelProps {
  readonly tabId: TabId;
}

export function StubPanel({ tabId }: StubPanelProps): JSX.Element {
  const { t } = useT();
  const tab = getTab(tabId);
  return (
    <section className="stub">
      <h2 className="stub__title">{tabLabel(t, tabId)}</h2>
      <p className="stub__hint">{tabHint(t, tabId)}</p>
      <p className="stub__wave">{t('app.stub.arrives', { wave: tab.wave })}</p>
    </section>
  );
}
