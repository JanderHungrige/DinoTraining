/**
 * Everything the trainer form needs to offer: datasets, backbones, head types.
 *
 * Head types are re-fetched whenever the backbone changes, because compatibility is a
 * property of the pair — asking once and caching would show a verdict for a backbone
 * the user is no longer training against.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import { listBackbones, type BackboneInfo } from '../api/backbones';
import { listDatasets, type DatasetInfo } from '../api/datasets';
import { listHeadTypes, type HeadTypeInfo } from '../api/heads';
import { useT } from '../i18n';

export interface UseTrainerOptionsResult {
  readonly datasets: readonly DatasetInfo[];
  readonly backbones: readonly BackboneInfo[];
  readonly headTypes: readonly HeadTypeInfo[];
  readonly loading: boolean;
  readonly error: string | null;
  readonly refresh: () => Promise<void>;
}

function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

/** Installed backbones only — a head cannot be trained against weights on the internet. */
export function installedOnly(backbones: readonly BackboneInfo[]): BackboneInfo[] {
  return backbones.filter((backbone) => backbone.installed);
}

export function useTrainerOptions(backboneId: string | null): UseTrainerOptionsResult {
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [backbones, setBackbones] = useState<readonly BackboneInfo[]>([]);
  const [headTypes, setHeadTypes] = useState<readonly HeadTypeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Through a ref: a language switch must not reload the options.
  const { t } = useT();
  const tr = useRef(t);
  tr.current = t;

  const load = useCallback(async (): Promise<void> => {
    setLoading(true);
    try {
      const [nextDatasets, nextBackbones] = await Promise.all([listDatasets(), listBackbones()]);
      setDatasets(nextDatasets);
      setBackbones(nextBackbones);
      setError(null);
    } catch (cause) {
      setError(describeError(cause, tr.current('training.error.options')));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    async function loadHeadTypes(): Promise<void> {
      try {
        // Without a backbone there is nothing to check against, so verdicts come back
        // null and every head type still lists — the user can see what exists.
        const next = await listHeadTypes(backboneId ?? undefined);
        if (!cancelled) setHeadTypes(next);
      } catch (cause) {
        if (!cancelled) setError(describeError(cause, tr.current('training.error.headTypes')));
      }
    }
    void loadHeadTypes();
    return () => {
      cancelled = true;
    };
  }, [backboneId]);

  return { datasets, backbones, headTypes, loading, error, refresh: load };
}
