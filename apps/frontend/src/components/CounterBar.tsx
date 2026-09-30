/**
 * Live annotation counters.
 *
 * Values come straight from the backend's aggregate, so this shows what is actually
 * persisted rather than what the UI believes it sent.
 */

import type { JSX } from 'react';

import type { DatasetCounts } from '../api/datasets';
import { useT } from '../i18n';

export interface CounterBarProps {
  readonly counts: DatasetCounts;
  readonly imageIndex: number;
  readonly imageTotal: number;
  readonly dirty: boolean;
}

export function CounterBar({
  counts,
  imageIndex,
  imageTotal,
  dirty,
}: CounterBarProps): JSX.Element {
  const { t } = useT();
  return (
    <div className="counters" role="status" aria-live="polite">
      <span className="counters__item">
        {t('studio.counter.image')} <strong>{imageTotal === 0 ? 0 : imageIndex + 1}</strong> / {imageTotal}
      </span>
      <span className="counters__sep" aria-hidden="true">
        ·
      </span>
      <span className="counters__item">
        {t('studio.counter.saved')} <strong>{counts.images}</strong>
      </span>
      {counts.masks > 0 && (
        <span className="counters__item">
          {t('studio.counter.masks')} <strong>{counts.masks}</strong>
        </span>
      )}
      <span className="counters__item counters__item--positive">
        {t('studio.counter.positive')} <strong>{counts.positive}</strong>
      </span>
      <span className="counters__item counters__item--negative">
        {t('studio.counter.negative')} <strong>{counts.negative}</strong>
      </span>
      <span className="counters__item counters__item--unclear">
        {t('studio.counter.unclear')} <strong>{counts.unclear}</strong>
      </span>
      {dirty && <span className="counters__dirty">{t('studio.counter.unsaved')}</span>}
    </div>
  );
}
