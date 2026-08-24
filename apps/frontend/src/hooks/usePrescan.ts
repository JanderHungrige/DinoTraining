/**
 * Running a prescan and watching it (doc 53).
 *
 * Polls every 1.5s. A scan reports once per image and can run for minutes, so a dropped
 * update costs one image's worth of progress and the next poll corrects it — the same
 * trade the fine-tune panel makes, for the same reason.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  cancelPrescan,
  isFinished,
  readPrescan,
  startPrescan,
  type PrescanJob,
  type StartPrescanOptions,
} from '../api/prescan';

const POLL_MS = 1500;

export interface PrescanState {
  readonly job: PrescanJob | null;
  readonly starting: boolean;
  readonly running: boolean;
  readonly error: string | null;
  readonly start: (options: StartPrescanOptions) => Promise<void>;
  readonly cancel: () => void;
  readonly clear: () => void;
}

export function usePrescan(): PrescanState {
  const [job, setJob] = useState<PrescanJob | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const running = job !== null && !isFinished(job);

  useEffect(() => {
    if (!running || job === null) return;
    const id = job.job_id;
    const timer = setInterval(() => {
      void readPrescan(id)
        .then((next) => {
          if (mounted.current) setJob(next);
        })
        .catch(() => {
          // One failed poll is not a failed scan — the job is still running on the server.
          // Reporting it would put an error on screen that the next tick contradicts.
        });
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [running, job?.job_id]);

  const start = useCallback(async (options: StartPrescanOptions): Promise<void> => {
    setStarting(true);
    setError(null);
    try {
      const started = await startPrescan(options);
      if (mounted.current) setJob(started);
    } catch (cause) {
      if (mounted.current) {
        setError(cause instanceof Error ? cause.message : 'Could not start the scan.');
      }
    } finally {
      if (mounted.current) setStarting(false);
    }
  }, []);

  const cancel = useCallback((): void => {
    if (job === null) return;
    void cancelPrescan(job.job_id)
      .then((next) => {
        if (mounted.current) setJob(next);
      })
      .catch(() => setError('Could not stop the scan.'));
  }, [job]);

  const clear = useCallback((): void => {
    setJob(null);
    setError(null);
  }, []);

  return { job, starting, running, error, start, cancel, clear };
}
