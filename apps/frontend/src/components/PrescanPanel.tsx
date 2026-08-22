/**
 * "Scan the folder first, then show me only what matters" (doc 53).
 *
 * A folder of 400 rail frames has a person in 30 of them. Reviewing it means pressing Next
 * 370 times to confirm nothing is there — the work this app exists to remove, being done by
 * hand.
 *
 * The scan runs **the same model the session is about to propose with**. Prescanning with
 * a different one would filter on one opinion and annotate on another, and every
 * disagreement would look like a bug in the proposer.
 *
 * Nothing here writes to the store. A model's silence is not an annotation, so a skipped
 * image is skipped and not recorded — and the filter is a toggle, so seeing every image
 * again costs one click and undoes nothing.
 */

import { useState, type JSX } from 'react';

import type { PrescanJob } from '../api/prescan';

export interface PrescanPanelProps {
  readonly total: number;
  readonly job: PrescanJob | null;
  readonly starting: boolean;
  readonly running: boolean;
  readonly error: string | null;
  readonly filtered: boolean;
  /** The classes this session's model can actually report, when it knows them. Offered as
   *  a hint rather than a fixed list: a prompt-based scan can look for anything. */
  readonly suggestions: readonly string[];
  readonly onScan: (labels: readonly string[], threshold: number) => void;
  readonly onCancel: () => void;
  readonly onApply: (apply: boolean) => void;
}

export function PrescanPanel({
  total,
  job,
  starting,
  running,
  error,
  filtered,
  suggestions,
  onScan,
  onCancel,
  onApply,
}: PrescanPanelProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const [labels, setLabels] = useState('');
  const [threshold, setThreshold] = useState(0.3);

  const parsed = labels
    .split(',')
    .map((label) => label.trim())
    .filter(Boolean);

  const done = job !== null && !running;
  const percent = job && job.total > 0 ? Math.round((job.scanned / job.total) * 100) : 0;

  if (!open) {
    return (
      <div className="prescan">
        <button type="button" className="btn btn--small" onClick={() => setOpen(true)}>
          <span aria-hidden="true">⚡</span> Skip the empty images…
        </button>
      </div>
    );
  }

  return (
    <section className="prescan prescan--open" aria-label="Prescan">
      <p className="prescan__lead">
        Run the model over all {total} image{total === 1 ? '' : 's'} first, then show only
        the ones it found something in. Nothing is saved — this only decides what you see.
      </p>

      <div className="prescan__controls">
        <label className="prescan__field" htmlFor="prescan-labels">
          Looking for
          <input
            id="prescan-labels"
            type="text"
            value={labels}
            placeholder={suggestions.length ? suggestions.join(', ') : 'person, bicycle'}
            disabled={running}
            onChange={(event) => setLabels(event.target.value)}
          />
          <span className="prescan__hint">
            Comma-separated. Leave empty to keep every image the model finds anything in.
          </span>
        </label>

        <label className="prescan__field" htmlFor="prescan-threshold">
          Confidence <span className="prescan__value">{threshold.toFixed(2)}</span>
          <input
            id="prescan-threshold"
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={threshold}
            disabled={running}
            onChange={(event) => setThreshold(Number(event.target.value))}
          />
        </label>
      </div>

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      {running && job ? (
        <div className="prescan__progress">
          <progress value={percent} max={100} aria-valuenow={percent} />
          <span>
            {job.scanned} of {job.total} · {job.hits.length} match
            {job.hits.length === 1 ? '' : 'es'} so far
          </span>
          <button type="button" className="btn btn--small" onClick={onCancel}>
            Stop, keep what it found
          </button>
        </div>
      ) : (
        <div className="prescan__actions">
          <button
            type="button"
            className="btn btn--primary btn--small"
            disabled={starting || total === 0}
            onClick={() => onScan(parsed, threshold)}
          >
            {starting ? 'Starting…' : `Scan ${total} image${total === 1 ? '' : 's'}`}
          </button>
          <button type="button" className="btn btn--small" onClick={() => setOpen(false)}>
            Close
          </button>
        </div>
      )}

      {done && job && (
        <div className="prescan__result" role="status">
          <p>
            <strong>
              {job.hits.length} of {job.total}
            </strong>{' '}
            image{job.hits.length === 1 ? '' : 's'} matched
            {job.state === 'cancelled' ? ' before you stopped it' : ''}
            {job.unreadable > 0 && (
              <>
                {' '}
                · <strong>{job.unreadable}</strong> could not be read
              </>
            )}
            {job.state === 'failed' && <> · the scan failed: {job.message}</>}
          </p>

          {/* The escape hatch the whole design rests on: the model may simply be wrong,
              and checking every image must never be more than one click away. */}
          <label className="prescan__toggle">
            <input
              type="checkbox"
              checked={filtered}
              disabled={job.hits.length === 0}
              onChange={(event) => onApply(event.target.checked)}
            />
            <span>
              Show only the {job.hits.length} match
              {job.hits.length === 1 ? '' : 'es'}
              {job.hits.length === 0 ? ' — nothing to show' : ''}
            </span>
          </label>
        </div>
      )}
    </section>
  );
}
