/** Follows a running import job until it ends (docs 136, 138). */

import { useEffect, useRef } from 'react';

import { getImportJob, type ImportJob } from '../api/datasetImport';

const POLL_MS = 700;

export function useImportJob(
  job: ImportJob | null,
  setJob: (job: ImportJob) => void,
  onImported: () => void,
  onError: (failure: unknown) => void,
): void {
  // The callbacks are often inline arrows; as dependencies they would restart the timer
  // on every render.
  const callbacks = useRef({ onImported, onError });
  useEffect(() => {
    callbacks.current = { onImported, onError };
  });

  useEffect(() => {
    if (job?.state !== 'running') return undefined;
    const timer = window.setTimeout(() => {
      void getImportJob(job.job_id)
        .then((next) => {
          setJob(next);
          if (next.state === 'complete') callbacks.current.onImported();
        })
        .catch((failure: unknown) => callbacks.current.onError(failure));
    }, POLL_MS);
    return () => window.clearTimeout(timer);
  }, [job, setJob]);
}
