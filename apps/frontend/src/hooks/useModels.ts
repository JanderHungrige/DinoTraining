/**
 * State for the Admin tab: catalogue, system info, and in-flight downloads.
 *
 * Download progress is polled rather than streamed. The backend already exposes a
 * job table, and polling survives a dropped connection without extra machinery —
 * SSE can replace this later without the UI noticing.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import {
  deleteModel,
  getDownloadJob,
  getSystemInfo,
  listModels,
  startDownload,
  type DownloadJob,
  type ModelInfo,
  type SystemInfo,
} from '../api/models';

const POLL_INTERVAL_MS = 750;

export interface UseModelsResult {
  readonly models: readonly ModelInfo[];
  readonly system: SystemInfo | null;
  readonly jobs: Readonly<Record<string, DownloadJob>>;
  readonly loading: boolean;
  readonly error: string | null;
  readonly busy: Readonly<Record<string, boolean>>;
  readonly download: (modelId: string) => Promise<void>;
  readonly remove: (modelId: string) => Promise<void>;
  readonly refresh: () => Promise<void>;
}

function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useModels(): UseModelsResult {
  const [models, setModels] = useState<readonly ModelInfo[]>([]);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [jobs, setJobs] = useState<Record<string, DownloadJob>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tracks whether the component is still mounted, so a late response from an
  // in-flight request cannot set state on an unmounted tree.
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const [nextModels, nextSystem] = await Promise.all([listModels(), getSystemInfo()]);
      if (!mounted.current) return;
      setModels(nextModels);
      setSystem(nextSystem);
      setError(null);
    } catch (cause) {
      if (mounted.current) setError(describeError(cause, 'Could not load the model catalogue.'));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const pollJob = useCallback(
    async (jobId: string): Promise<void> => {
      while (mounted.current) {
        let job: DownloadJob;
        try {
          job = await getDownloadJob(jobId);
        } catch (cause) {
          if (mounted.current) setError(describeError(cause, 'Lost track of the download.'));
          return;
        }

        if (!mounted.current) return;
        setJobs((current) => ({ ...current, [job.model_id]: job }));

        if (job.state === 'complete' || job.state === 'failed') {
          // Refresh first: it clears `error` on success, so reporting the failure
          // before it would silently wipe the message the user needs.
          await refresh();
          if (job.state === 'failed' && mounted.current) {
            setError(job.message || 'Download failed.');
          }
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      }
    },
    [refresh],
  );

  const download = useCallback(
    async (modelId: string): Promise<void> => {
      setBusy((current) => ({ ...current, [modelId]: true }));
      try {
        const job = await startDownload(modelId);
        if (!mounted.current) return;
        setJobs((current) => ({ ...current, [modelId]: job }));
        setError(null);
        await pollJob(job.job_id);
      } catch (cause) {
        if (mounted.current) setError(describeError(cause, 'Could not start the download.'));
      } finally {
        if (mounted.current) setBusy((current) => ({ ...current, [modelId]: false }));
      }
    },
    [pollJob],
  );

  const remove = useCallback(
    async (modelId: string): Promise<void> => {
      setBusy((current) => ({ ...current, [modelId]: true }));
      try {
        await deleteModel(modelId);
        if (!mounted.current) return;
        setJobs((current) => {
          const next = { ...current };
          delete next[modelId];
          return next;
        });
        setError(null);
        await refresh();
      } catch (cause) {
        if (mounted.current) setError(describeError(cause, 'Could not remove the model.'));
      } finally {
        if (mounted.current) setBusy((current) => ({ ...current, [modelId]: false }));
      }
    },
    [refresh],
  );

  return { models, system, jobs, loading, error, busy, download, remove, refresh };
}
