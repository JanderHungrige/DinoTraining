/**
 * One fine-tune at a time (doc 97): start, poll until it finishes, cancel. And the
 * readiness check for the current choice, run again whenever the choice changes.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  cancelFinetune,
  checkReadiness,
  getFinetuneJob,
  startFinetune,
  type FinetuneJobInfo,
  type Readiness,
  type StartFinetune,
} from '../api/finetune';

const POLL_MS = 2000;
const FINISHED = new Set(['complete', 'failed', 'cancelled']);

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function useReadiness(finetuneId: string, datasetId: string, recipeId: string): {
  readiness: Readiness | null;
  error: string;
} {
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    setReadiness(null);
    setError('');
    if (!finetuneId || !datasetId) return;
    let live = true;
    checkReadiness(finetuneId, datasetId, recipeId || undefined)
      .then((found) => live && setReadiness(found))
      .catch((cause: unknown) => live && setError(message(cause)));
    return () => {
      live = false;
    };
  }, [finetuneId, datasetId, recipeId]);
  return { readiness, error };
}

export interface FoundationFinetune {
  readonly job: FinetuneJobInfo | null;
  readonly starting: boolean;
  readonly error: string;
  readonly running: boolean;
  readonly start: (request: StartFinetune) => Promise<void>;
  readonly cancel: () => Promise<void>;
}

export function useFoundationFinetune(): FoundationFinetune {
  const [job, setJob] = useState<FinetuneJobInfo | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const timer = useRef<number | null>(null);

  const stop = (): void => {
    if (timer.current !== null) window.clearInterval(timer.current);
    timer.current = null;
  };
  useEffect(() => stop, []);

  const poll = useCallback((jobId: string) => {
    stop();
    timer.current = window.setInterval(() => {
      getFinetuneJob(jobId)
        .then((next) => {
          setJob(next);
          if (FINISHED.has(next.state)) stop();
        })
        .catch((cause: unknown) => {
          setError(message(cause));
          stop();
        });
    }, POLL_MS);
  }, []);

  const start = useCallback(
    async (request: StartFinetune) => {
      setStarting(true);
      setError('');
      try {
        const created = await startFinetune(request);
        setJob(created);
        poll(created.job_id);
      } catch (cause) {
        setError(message(cause));
      } finally {
        setStarting(false);
      }
    },
    [poll],
  );

  const cancel = useCallback(async () => {
    if (!job) return;
    try {
      await cancelFinetune(job.job_id);
    } catch (cause) {
      setError(message(cause));
    }
  }, [job]);

  const running = job !== null && !FINISHED.has(job.state);
  return { job, starting, error, running, start, cancel };
}
