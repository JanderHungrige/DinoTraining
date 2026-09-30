/**
 * Hidden autoplay's only output while it runs, and every run's summary when it ends
 * (doc 71).
 */

import type { JSX } from 'react';

import { useT, type Translator } from '../i18n';
import { emptyProgress, type AutoplayProgress as Progress, type AutoplayReport } from '../lib/autoplay';

function tallyText(progress: Progress, { t }: Translator): string {
  const parts = [
    t('generator.autoplay.saved', { count: progress.saved }),
    t('generator.autoplay.empty', { count: progress.empty }),
  ];
  if (progress.failed > 0) parts.push(t('generator.autoplay.failed', { count: progress.failed }));
  if (progress.skipped > 0) parts.push(t('generator.autoplay.skipped', { count: progress.skipped }));
  if (progress.asked > 0) parts.push(t('generator.autoplay.asked', { count: progress.asked }));
  return parts.join(' · ');
}

export function percentOf(progress: Progress): number {
  return progress.total === 0 ? 100 : Math.round((progress.done / progress.total) * 100);
}

export function AutoplayBar({ progress }: { readonly progress: Progress | null }): JSX.Element {
  const tr = useT();
  const shown = progress ?? emptyProgress(0);
  const percent = progress === null ? 0 : percentOf(shown);
  return (
    <div className="autoplay">
      <p className="autoplay__head">
        <strong>{percent} %</strong>{' '}
        {tr.t('generator.autoplay.runningHidden', { done: shown.done, total: shown.total })}
      </p>
      <progress
        className="autoplay__bar"
        max={100}
        value={percent}
        aria-label={tr.t('generator.autoplay.progressAria', { percent })}
      />
      <p className="autoplay__tally">{tallyText(shown, tr)}</p>
    </div>
  );
}

const ENDINGS = {
  finished: 'generator.autoplay.finished',
  stopped: 'generator.autoplay.stopped',
  'save-failed': 'generator.autoplay.saveFailed',
} as const satisfies Record<AutoplayReport['end'], string>;

export function AutoplaySummary({ report }: { readonly report: AutoplayReport }): JSX.Element {
  const tr = useT();
  return (
    <p className="autoplay__summary" role="status">
      {tr.t(ENDINGS[report.end])} {tallyText(report, tr)}.
      {report.lastError ? ` ${tr.t('generator.autoplay.lastFailure', { error: report.lastError })}` : ''}
    </p>
  );
}
