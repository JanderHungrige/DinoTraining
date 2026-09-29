/**
 * Hidden autoplay's only output while it runs, and every run's summary when it ends
 * (doc 71).
 */

import type { JSX } from 'react';

import type { AutoplayProgress as Progress, AutoplayReport } from '../lib/autoplay';

function tallyText(progress: Progress): string {
  const parts = [`${progress.saved} saved`, `${progress.empty} with nothing found`];
  if (progress.failed > 0) parts.push(`${progress.failed} failed`);
  if (progress.skipped > 0) parts.push(`${progress.skipped} already saved`);
  return parts.join(' · ');
}

export function percentOf(progress: Progress): number {
  return progress.total === 0 ? 100 : Math.round((progress.done / progress.total) * 100);
}

export function AutoplayBar({ progress }: { readonly progress: Progress | null }): JSX.Element {
  const shown = progress ?? { done: 0, total: 0, saved: 0, empty: 0, failed: 0, skipped: 0 };
  const percent = progress === null ? 0 : percentOf(shown);
  return (
    <div className="autoplay">
      <p className="autoplay__head">
        <strong>{percent} %</strong> — running hidden, image {shown.done} of {shown.total}
      </p>
      <progress
        className="autoplay__bar"
        max={100}
        value={percent}
        aria-label={`Autoplay progress, ${percent} percent`}
      />
      <p className="autoplay__tally">{tallyText(shown)}</p>
    </div>
  );
}

const ENDINGS: Record<AutoplayReport['end'], string> = {
  finished: 'Autoplay reached the last image.',
  stopped: 'Autoplay stopped here. Correct anything that is wrong; moving on saves it.',
  'save-failed': 'Autoplay stopped because an image could not be saved.',
};

export function AutoplaySummary({ report }: { readonly report: AutoplayReport }): JSX.Element {
  return (
    <p className="autoplay__summary" role="status">
      {ENDINGS[report.end]} {tallyText(report)}.
      {report.lastError ? ` Last failure: ${report.lastError}` : ''}
    </p>
  );
}
