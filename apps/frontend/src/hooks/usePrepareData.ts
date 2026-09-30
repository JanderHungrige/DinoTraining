/**
 * What the Prepare flow knows about one dataset (doc 89): its last audit, its fixes, its
 * split and its recipes, with the actions that change them.
 *
 * Everything here is *loaded*, never seeded into state from props: the flow's choices
 * (grid, strategy, preset) live in the tab as overrides of the loaded recommendation.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  applyFix,
  getAuditJob,
  getLastAudit,
  getPrepState,
  getSplit,
  makeSplit,
  startAudit,
  type DatasetAudit,
  type FixAction,
  type PrepState,
  type SplitReport,
} from '../api/prep';
import { listRecipes, type RecipeInfo } from '../api/prepPlan';

const POLL_MS = 400;

export interface AuditProgress {
  readonly done: number;
  readonly total: number;
}

export interface PrepareData {
  readonly audit: DatasetAudit | null;
  readonly auditing: AuditProgress | null;
  readonly state: PrepState | null;
  readonly split: SplitReport | null;
  readonly recipes: readonly RecipeInfo[];
  readonly busy: boolean;
  readonly error: string;
  readonly runAudit: (target: string) => void;
  readonly fix: (
    action: FixAction,
    extra?: { paths?: readonly string[]; class_map?: Readonly<Record<string, string | null>> },
  ) => Promise<number>;
  readonly split_: (mode: 'auto' | 'keep-source') => Promise<void>;
  readonly reloadRecipes: () => void;
}

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function usePrepareData(datasetId: string): PrepareData {
  const [audit, setAudit] = useState<DatasetAudit | null>(null);
  const [auditing, setAuditing] = useState<AuditProgress | null>(null);
  const [state, setState] = useState<PrepState | null>(null);
  const [split, setSplit] = useState<SplitReport | null>(null);
  const [recipes, setRecipes] = useState<readonly RecipeInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const current = useRef(datasetId);
  current.current = datasetId;

  const reloadRecipes = useCallback(() => {
    if (!datasetId) return;
    listRecipes(datasetId)
      .then((found) => current.current === datasetId && setRecipes(found))
      .catch((cause: unknown) => setError(message(cause)));
  }, [datasetId]);

  useEffect(() => {
    setAudit(null);
    setState(null);
    setSplit(null);
    setRecipes([]);
    setError('');
    if (!datasetId) return;
    Promise.all([getLastAudit(datasetId), getPrepState(datasetId), getSplit(datasetId)])
      .then(([lastAudit, prepState, stored]) => {
        if (current.current !== datasetId) return; // the user moved on to another dataset
        setAudit(lastAudit);
        setState(prepState);
        setSplit(stored);
      })
      .catch((cause: unknown) => setError(message(cause)));
    reloadRecipes();
  }, [datasetId, reloadRecipes]);

  const runAudit = useCallback(
    (target: string) => {
      setError('');
      setAuditing({ done: 0, total: 0 });
      const poll = (jobId: string): void => {
        getAuditJob(jobId)
          .then((job) => {
            if (job.state === 'complete' && job.audit) {
              setAudit(job.audit);
              setAuditing(null);
            } else if (job.state === 'failed') {
              setError(job.message || 'The audit failed.');
              setAuditing(null);
            } else {
              setAuditing({ done: job.done, total: job.total });
              window.setTimeout(() => poll(jobId), POLL_MS);
            }
          })
          .catch((cause: unknown) => {
            setError(message(cause));
            setAuditing(null);
          });
      };
      startAudit(datasetId, target)
        .then((job) => poll(job.job_id))
        .catch((cause: unknown) => {
          setError(message(cause));
          setAuditing(null);
        });
    },
    [datasetId],
  );

  const fix = useCallback<PrepareData['fix']>(
    async (action, extra = {}) => {
      setBusy(true);
      setError('');
      try {
        const result = await applyFix(datasetId, action, extra);
        setState(result.state);
        return result.changed;
      } catch (cause) {
        setError(message(cause));
        return 0;
      } finally {
        setBusy(false);
      }
    },
    [datasetId],
  );

  const split_ = useCallback<PrepareData['split_']>(
    async (mode) => {
      setBusy(true);
      setError('');
      try {
        setSplit(await makeSplit(datasetId, { mode }));
      } catch (cause) {
        setError(message(cause));
      } finally {
        setBusy(false);
      }
    },
    [datasetId],
  );

  return { audit, auditing, state, split, recipes, busy, error, runAudit, fix, split_, reloadRecipes };
}
