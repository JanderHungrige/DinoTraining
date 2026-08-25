/**
 * What the Inference Viewer can offer to run: installed heads, installed foundation
 * models, and the datasets those heads were trained on.
 *
 * Extracted from `useHeadRun` when that crossed the project's 300-line gate. The seam is a
 * real one: everything here is "what exists", loaded once and never changed by the user,
 * and everything left there is selection, running and result-gating.
 *
 * **Three catalogues, three effects, three failure policies** — deliberately not merged
 * into one request. A head listing that fails takes the panel down, because there is
 * nothing to run. A foundation listing that fails must not, because the heads still work.
 * A dataset listing that fails should cost the *filter* and nothing else. One combined
 * request would flatten all three into a single failure and take the whole surface with it.
 */

import { useEffect, useMemo, useState } from 'react';

import { ApiError } from '../api/client';
import { listDatasets, type DatasetInfo } from '../api/datasets';
import { listFoundations, type FoundationInfo } from '../api/foundation';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';

export interface RunnableModels {
  readonly heads: readonly HeadInstanceInfo[];
  /** Installed foundation models only. */
  readonly foundations: readonly FoundationInfo[];
  /** Every dataset some installed head was trained on, id → name, for the filter. */
  readonly trainedOn: readonly { readonly id: string; readonly name: string }[];
  readonly loadingHeads: boolean;
  /** Set only when the *heads* fail to load — the one catalogue nothing works without. */
  readonly error: string | null;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

export function useRunnableModels(): RunnableModels {
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [foundations, setFoundations] = useState<readonly FoundationInfo[]>([]);
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [loadingHeads, setLoadingHeads] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    void listHeadInstances({}, controller.signal)
      .then((found) => {
        if (controller.signal.aborted) return;
        setHeads(found);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted) setError(describe(cause, 'Could not load heads.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingHeads(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void listFoundations(controller.signal)
      .then((found) => {
        if (controller.signal.aborted) return;
        // Only installed ones are offered here. The admin panel is where a model is
        // downloaded; listing an absent one in the runner would offer an action whose
        // only outcome is a 409 telling you to go somewhere else.
        setFoundations(found.filter((entry) => entry.installed));
      })
      .catch(() => {
        // Non-fatal: heads still run. A foundation model failing to list must not take
        // the whole panel down with it.
        if (!controller.signal.aborted) setFoundations([]);
      });
    return () => controller.abort();
  }, []);

  // Names only — the filter matches on `dataset_ids`, which every head already carries.
  // Its own effect rather than the heads' one: a dataset list that fails to load should
  // cost the filter, not the panel.
  useEffect(() => {
    const controller = new AbortController();
    void listDatasets(controller.signal)
      .then(setDatasets)
      .catch(() => setDatasets([]));
    return () => controller.abort();
  }, []);

  const trainedOn = useMemo(() => {
    const used = new Set(heads.flatMap((head) => head.dataset_ids));
    return datasets
      .filter((dataset) => used.has(dataset.id))
      .map((dataset) => ({ id: dataset.id, name: dataset.name }));
  }, [heads, datasets]);

  return { heads, foundations, trainedOn, loadingHeads, error };
}
