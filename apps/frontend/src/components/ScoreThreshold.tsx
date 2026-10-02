/**
 * The Inference Viewer's detection threshold and its "why is this empty" note (2026-10-02).
 * Filtering happens in the browser (`lib/scoreFilter.ts`), so the slider needs no new run.
 */

import type { JSX } from 'react';

import type { Prediction } from '../api/inference';
import { useT } from '../i18n';
import { emptyBecause } from '../lib/scoreFilter';

export function ScoreSlider({ value, onChange }: { readonly value: number; readonly onChange: (value: number) => void }): JSX.Element {
  const { t } = useT();
  return (
    <label className="viewer__threshold">
      {t('run.viewer.minScore')}{' '}
      <input type="range" min={0.05} max={0.95} step={0.05} value={value} onChange={(event) => onChange(Number(event.target.value))} />{' '}
      <output>{value.toFixed(2)}</output>
    </label>
  );
}

/** Says why a detection pane is empty: nothing above the threshold, or nothing at all. */
export function ScoreNote({ prediction, minScore }: { readonly prediction: Prediction; readonly minScore: number }): JSX.Element | null {
  const { t } = useT();
  const empty = emptyBecause(prediction, minScore);
  if (!empty) return null;
  return (
    <p className="viewer__placeholder viewer__note" role="status">
      {empty.best === null
        ? t('run.viewer.noneAtAll')
        : t('run.viewer.noneAbove', { threshold: minScore.toFixed(2), best: empty.best.toFixed(2) })}
    </p>
  );
}
