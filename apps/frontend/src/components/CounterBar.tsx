/**
 * Live annotation counters.
 *
 * Values come straight from the backend's aggregate, so this shows what is actually
 * persisted rather than what the UI believes it sent.
 */

import type { JSX } from 'react';

import type { DatasetCounts } from '../api/datasets';

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
  return (
    <div className="counters" role="status" aria-live="polite">
      <span className="counters__item">
        Image <strong>{imageTotal === 0 ? 0 : imageIndex + 1}</strong> / {imageTotal}
      </span>
      <span className="counters__sep" aria-hidden="true">
        ·
      </span>
      <span className="counters__item">
        Saved images <strong>{counts.images}</strong>
      </span>
      <span className="counters__item counters__item--positive">
        Positive <strong>{counts.positive}</strong>
      </span>
      <span className="counters__item counters__item--negative">
        Negative <strong>{counts.negative}</strong>
      </span>
      <span className="counters__item counters__item--unclear">
        Unclear <strong>{counts.unclear}</strong>
      </span>
      {dirty && <span className="counters__dirty">Unsaved changes</span>}
    </div>
  );
}
