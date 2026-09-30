/**
 * Making a model's default recipe (doc 101): start the job, follow its step, and hand the
 * saved recipe to the caller.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { getDefaultRecipeJob, startDefaultRecipe, type ModelRef } from '../api/defaultRecipe';
import type { Recipe } from '../api/prepPlan';
import { useT } from '../i18n';

const POLL_MS = 500;

export interface DefaultRecipe {
  readonly busy: boolean;
  /** The step running now, or the outcome. */
  readonly message: string;
  readonly error: string;
  readonly create: () => void;
}

export function useDefaultRecipe(
  datasetId: string,
  model: ModelRef | null,
  onSaved: (recipe: Recipe) => void,
): DefaultRecipe {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const timer = useRef<number | undefined>(undefined);
  const saved = useRef(onSaved);
  saved.current = onSaved;
  const { t } = useT();
  const tr = useRef(t);
  tr.current = t;

  useEffect(() => () => window.clearInterval(timer.current), []);

  const follow = useCallback((jobId: string) => {
    timer.current = window.setInterval(() => {
      getDefaultRecipeJob(jobId)
        .then((job) => {
          setMessage(job.message);
          if (job.state === 'running' || job.state === 'pending') return;
          window.clearInterval(timer.current);
          setBusy(false);
          if (job.state === 'complete' && job.recipe) saved.current(job.recipe);
          else setError(job.message || tr.current('training.explainer.failed'));
        })
        .catch((cause: unknown) => {
          window.clearInterval(timer.current);
          setBusy(false);
          setError(cause instanceof Error ? cause.message : String(cause));
        });
    }, POLL_MS);
  }, []);

  const create = useCallback(() => {
    if (!datasetId || !model) return;
    setBusy(true);
    setError('');
    setMessage(tr.current('training.explainer.starting'));
    startDefaultRecipe(datasetId, model)
      .then((job) => follow(job.job_id))
      .catch((cause: unknown) => {
        setBusy(false);
        setError(cause instanceof Error ? cause.message : String(cause));
      });
  }, [datasetId, model, follow]);

  return { busy, message, error, create };
}
