/**
 * One training run: start it, follow its SSE stream, cancel it.
 *
 * The stream is the source of truth while running. On mount it reattaches to any job
 * still in flight — the backend re-sends a full snapshot on connect, so leaving the tab
 * and coming back reconstructs the run rather than losing it.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import {
  cancelTrainingJob,
  listTrainingJobs,
  startTraining,
  streamTrainingJob,
  TERMINAL_STATES,
  type EpochInfo,
  type JobInfo,
  type TrainingRequest,
} from '../api/training';

export interface UseTrainingRunResult {
  readonly job: JobInfo | null;
  readonly history: readonly EpochInfo[];
  readonly starting: boolean;
  readonly error: string | null;
  readonly running: boolean;
  readonly start: (request: TrainingRequest) => Promise<void>;
  readonly cancel: () => Promise<void>;
  readonly clear: () => void;
}

function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export interface UseTrainingRunOptions {
  /** Called once a run reaches a terminal state — used to refresh the saved-head list. */
  readonly onComplete?: (job: JobInfo) => void;
}

export function useTrainingRun(options: UseTrainingRunOptions = {}): UseTrainingRunResult {
  const [job, setJob] = useState<JobInfo | null>(null);
  const [history, setHistory] = useState<readonly EpochInfo[]>([]);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const unsubscribe = useRef<(() => void) | null>(null);
  const onComplete = useRef(options.onComplete);
  onComplete.current = options.onComplete;

  const attach = useCallback((jobId: string) => {
    unsubscribe.current?.();
    unsubscribe.current = streamTrainingJob(jobId, {
      onStatus: (next) => {
        setJob(next);
        // A snapshot carries the whole history, which is what makes reconnecting
        // lossless rather than resuming from wherever the client happened to be.
        if (next.history.length) setHistory(next.history);
      },
      onEpoch: (entry) => {
        setHistory((current) =>
          current.some((existing) => existing.epoch === entry.epoch)
            ? current
            : [...current, entry],
        );
      },
      onDone: (next) => {
        setJob(next);
        if (next.history.length) setHistory(next.history);
        onComplete.current?.(next);
      },
      onError: () => setError('Lost the training stream. The run may still be going.'),
    });
  }, []);

  // Reattach to a job that is still running from a previous mount.
  useEffect(() => {
    let cancelled = false;
    async function reattach(): Promise<void> {
      try {
        const jobs = await listTrainingJobs();
        const live = jobs.find((candidate) => !TERMINAL_STATES.includes(candidate.state));
        if (!cancelled && live) {
          setJob(live);
          setHistory(live.history);
          attach(live.job_id);
        }
      } catch {
        // Nothing to reattach to is the normal case, not an error worth showing.
      }
    }
    void reattach();
    return () => {
      cancelled = true;
      unsubscribe.current?.();
      unsubscribe.current = null;
    };
  }, [attach]);

  const start = useCallback(
    async (request: TrainingRequest): Promise<void> => {
      setStarting(true);
      setError(null);
      setHistory([]);
      try {
        const next = await startTraining(request);
        setJob(next);
        attach(next.job_id);
      } catch (cause) {
        setError(describeError(cause, 'Could not start training.'));
      } finally {
        setStarting(false);
      }
    },
    [attach],
  );

  const cancel = useCallback(async (): Promise<void> => {
    if (!job) return;
    try {
      await cancelTrainingJob(job.job_id);
    } catch (cause) {
      setError(describeError(cause, 'Could not cancel the run.'));
    }
  }, [job]);

  const clear = useCallback((): void => {
    unsubscribe.current?.();
    unsubscribe.current = null;
    setJob(null);
    setHistory([]);
    setError(null);
  }, []);

  const running = job !== null && !TERMINAL_STATES.includes(job.state);

  return { job, history, starting, error, running, start, cancel, clear };
}
