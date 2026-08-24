/**
 * Live training progress: state, epoch table and inline metric sparklines.
 *
 * Metric names are read from the payload via `metricKeys`, never hardcoded — a head
 * type reporting mIoU charts here without a frontend change. The primary metric is
 * highlighted, and which one that is also comes from the backend.
 *
 * SVG rather than a charting library: two series do not justify installer weight, and a
 * table is readable by a screen reader in a way a canvas chart is not.
 */

import type { JSX } from 'react';

import { metricKeys, type EpochInfo, type JobInfo } from '../api/training';

export interface TrainingProgressProps {
  readonly job: JobInfo;
  readonly history: readonly EpochInfo[];
  readonly onCancel: () => void;
}

const STATE_LABELS: Readonly<Record<string, string>> = Object.freeze({
  pending: 'Queued',
  running: 'Training',
  complete: 'Complete',
  failed: 'Failed',
  cancelled: 'Cancelled',
});

/** Normalise a series to a 0–1 sparkline path. Flat series sit mid-height rather than
 *  collapsing to a line at zero, which would read as "no data". */
export function sparklinePath(values: readonly number[], width = 120, height = 24): string {
  if (values.length === 0) return '';
  if (values.length === 1) return `M0,${height / 2} L${width},${height / 2}`;

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  const step = width / (values.length - 1);

  return values
    .map((value, index) => {
      const ratio = span === 0 ? 0.5 : (value - min) / span;
      const y = height - ratio * height;
      return `${index === 0 ? 'M' : 'L'}${(index * step).toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
}

function Sparkline({ values, accent }: { values: readonly number[]; accent: boolean }): JSX.Element {
  return (
    <svg className="spark" viewBox="0 0 120 24" role="presentation" aria-hidden="true">
      <path
        d={sparklinePath(values)}
        fill="none"
        stroke={accent ? 'var(--accent)' : 'var(--text-dim)'}
        strokeWidth="1.5"
      />
    </svg>
  );
}

export function TrainingProgress({ job, history, onCancel }: TrainingProgressProps): JSX.Element {
  const keys = metricKeys(history);
  const running = job.state === 'running' || job.state === 'pending';
  const percent = job.total_epochs ? Math.round((job.epoch / job.total_epochs) * 100) : 0;

  return (
    <section className="run" aria-live="polite">
      <header className="run__head">
        <h3 className="run__title">
          {STATE_LABELS[job.state] ?? job.state}
          <span className="trainer__dim">
            {' '}
            · epoch {job.epoch}/{job.total_epochs}
          </span>
        </h3>
        {running && (
          <button className="btn btn--danger" type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </header>

      <div className="progress">
        <div className="progress__bar" style={{ width: `${percent}%` }} />
      </div>

      {job.message && <p className="run__message">{job.message}</p>}

      {job.skipped_mixed_class_images > 0 && (
        /* Surfaced, never silent: training on fewer images than the user annotated is
           exactly the quiet loss this project keeps designing against. */
        <p className="run__warn">
          {job.skipped_mixed_class_images} image(s) skipped — their boxes name more than one
          class, which classification cannot use.
        </p>
      )}

      {job.class_names.length > 0 && (
        <p className="run__classes">
          Classes: <code>{job.class_names.join(', ')}</code>
        </p>
      )}

      {history.length > 0 && (
        <>
          <div className="run__sparks">
            {keys.map((key) => (
              <div key={key} className="run__spark">
                <span className={key === job.primary_metric ? 'run__key run__key--primary' : 'run__key'}>
                  {key}
                  {key === job.primary_metric ? ' (best-model criterion)' : ''}
                </span>
                <Sparkline
                  values={history.map((entry) => entry.metrics[key] ?? 0)}
                  accent={key === job.primary_metric}
                />
                <span className="run__last">
                  {(history[history.length - 1]?.metrics[key] ?? 0).toFixed(3)}
                </span>
              </div>
            ))}
          </div>

          <table className="run__table">
            <caption className="run__caption">Per-epoch loss and metrics</caption>
            <thead>
              <tr>
                <th scope="col">Epoch</th>
                <th scope="col">Train loss</th>
                <th scope="col">Val loss</th>
                {keys.map((key) => (
                  <th key={key} scope="col">
                    {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.epoch} className={entry.epoch === job.best_epoch ? 'run__best' : ''}>
                  <th scope="row">{entry.epoch}</th>
                  <td>{entry.train_loss.toFixed(4)}</td>
                  <td>{entry.val_loss.toFixed(4)}</td>
                  {keys.map((key) => (
                    <td key={key}>{(entry.metrics[key] ?? 0).toFixed(3)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {job.head_instance_id && (
        <p className="run__saved">Saved as a head you can now use in the Inference Viewer.</p>
      )}
    </section>
  );
}
