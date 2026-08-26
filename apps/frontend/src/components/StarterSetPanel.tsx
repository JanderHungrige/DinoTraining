/**
 * One button that makes a fresh install useful (doc 65).
 *
 * **Nothing is bundled, and cannot be.** The starter set is ~1.1 GB — too much for a git
 * clone, several times the whole installer (doc 56 measured it at 181–377 MB), and the
 * gated models may not be redistributed at all, which is what the licence acceptance is
 * for. So the goal was never zero clicks; it was *one*, instead of working out which five
 * of fifteen models matter and pressing five buttons in the right order.
 *
 * **The set is declared in the catalogue, not here.** `starter` is a field on the model,
 * so "what a new user needs" is answered next to the models and the UI cannot disagree
 * with the API about it.
 *
 * Downloads run **one at a time**. Five parallel HuggingFace pulls saturate the link and
 * make every progress bar lie about its own speed; sequential is slower to start and
 * honest throughout.
 */

import { useCallback, useState, type JSX } from 'react';

import type { DownloadJob, ModelInfo } from '../api/models';

export interface StarterSetPanelProps {
  readonly models: readonly ModelInfo[];
  readonly jobs: Readonly<Record<string, DownloadJob>>;
  readonly onDownload: (modelId: string) => Promise<void>;
}

/** Job states that mean work is happening. `pending` counts: the download is claimed. */
const IN_FLIGHT: ReadonlySet<string> = new Set(['pending', 'downloading']);

/**
 * What to show beside a model mid-download.
 *
 * Percent only when the total is actually known — HuggingFace does not always send a
 * content length, and `0 / 0` renders as a confident `NaN%` or a bar stuck at zero, both
 * of which read as a stall rather than as a missing number.
 */
function progressOf(job: DownloadJob | undefined): string {
  if (!job) return '';
  if (job.state === 'complete') return 'done';
  if (job.state === 'failed') return 'failed';
  if (job.total_bytes > 0) {
    return `${Math.round((job.downloaded_bytes / job.total_bytes) * 100)}%`;
  }
  return job.downloaded_bytes > 0 ? `${Math.round(job.downloaded_bytes / 1e6)} MB` : '…';
}

/** What a first run needs, and what of it is still missing. */
export function starterState(models: readonly ModelInfo[]) {
  const starter = models.filter((model) => model.starter);
  const missing = starter.filter((model) => !model.installed);
  return {
    starter,
    missing,
    megabytes: missing.reduce((total, model) => total + model.approx_size_mb, 0),
  };
}

export function StarterSetPanel({
  models,
  jobs,
  onDownload,
}: StarterSetPanelProps): JSX.Element | null {
  const [running, setRunning] = useState(false);
  const { starter, missing, megabytes } = starterState(models);

  const start = useCallback(async (): Promise<void> => {
    setRunning(true);
    try {
      // Sequential on purpose — see the note at the top of the file.
      for (const model of missing) {
        await onDownload(model.id);
      }
    } finally {
      setRunning(false);
    }
  }, [missing, onDownload]);

  // Nothing to offer once the catalogue has not loaded, or once it is all here.
  if (starter.length === 0) return null;

  if (missing.length === 0) {
    return (
      <div className="starter starter--done">
        <strong>Ready to use.</strong> Every model a first run needs is installed —
        annotate from a prompt, train a head, fine-tune a detector, or run depth.
      </div>
    );
  }

  const active = missing.some((model) => IN_FLIGHT.has(jobs[model.id]?.state ?? ''));

  return (
    <div className="starter">
      <h3 className="starter__title">Set this up</h3>
      <p className="starter__body">
        Nothing is bundled with the app — weights download on demand and are cached, so
        this is once per machine. These {missing.length} give you every feature: a backbone
        for trained heads, a general detector, both halves of Grounded SAM, and depth.
      </p>

      <ul className="starter__list">
        {missing.map((model) => (
          <li key={model.id} className="starter__item">
            <code className="starter__id">{model.id}</code>
            <span className="starter__size">{model.approx_size_mb} MB</span>
            <span className="starter__state">{progressOf(jobs[model.id])}</span>
          </li>
        ))}
      </ul>

      <button
        type="button"
        className="btn btn--primary"
        disabled={running || active}
        onClick={() => void start()}
      >
        {running || active
          ? 'Downloading…'
          : `Download all ${missing.length} (${(megabytes / 1000).toFixed(1)} GB)`}
      </button>
      {/* Said before the click, not after: a gigabyte is a real decision on a phone
          tether or a metered connection. */}
      <span className="starter__note">
        One at a time, so the progress figures mean something. You can keep using the app.
      </span>
    </div>
  );
}
