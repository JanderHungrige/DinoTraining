/**
 * Starting and watching a fine-tune (doc 44 UI).
 *
 * **Polling, not SSE.** Head training streams because its epochs land in seconds and a
 * dropped update is visible; a fine-tune epoch takes tens of seconds, so a poll every few
 * seconds costs nothing and needs no stream to keep alive across a laptop sleeping.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import {
  cancelFinetune,
  readFinetune,
  startFinetune,
  type FinetuneJob,
  type StartFinetuneOptions,
} from '../api/foundation';

/** Slow enough not to hammer a machine that is busy training, fast enough to feel live. */
const POLL_MS = 3000;

export interface FinetuneState {
  readonly job: FinetuneJob | null;
  readonly starting: boolean;
  readonly running: boolean;
  readonly error: string | null;
  readonly start: (options: StartFinetuneOptions) => Promise<void>;
  readonly cancel: () => Promise<void>;
  readonly dismiss: () => void;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

export function useFinetune(): FinetuneState {
  const [job, setJob] = useState<FinetuneJob | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const jobId = job?.job_id ?? null;
  const running = job?.state === 'running' || job?.state === 'pending';

  // The poll reads through a ref so the effect depends only on the id and whether it is
  // still running — re-subscribing on every tick would reset the interval forever.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  useEffect(() => {
    if (jobId === null || !running) return;
    const controller = new AbortController();

    const timer = setInterval(() => {
      void readFinetune(jobId, controller.signal)
        .then((next) => {
          if (mounted.current && !controller.signal.aborted) setJob(next);
        })
        .catch(() => {
          // A single failed poll is not worth surfacing: the next one is three seconds
          // away and the run itself is unaffected.
        });
    }, POLL_MS);

    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [jobId, running]);

  const start = useCallback(async (options: StartFinetuneOptions): Promise<void> => {
    setStarting(true);
    setError(null);
    try {
      setJob(await startFinetune(options));
    } catch (cause) {
      setError(describe(cause, 'Could not start fine-tuning.'));
    } finally {
      setStarting(false);
    }
  }, []);

  const cancel = useCallback(async (): Promise<void> => {
    if (jobId === null) return;
    try {
      setJob(await cancelFinetune(jobId));
    } catch (cause) {
      setError(describe(cause, 'Could not cancel the run.'));
    }
  }, [jobId]);

  const dismiss = useCallback((): void => {
    setJob(null);
    setError(null);
  }, []);

  return { job, starting, running, error, start, cancel, dismiss };
}
