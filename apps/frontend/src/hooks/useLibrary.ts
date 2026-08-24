/**
 * Everything the user has made, in one place (doc 51).
 *
 * Three separate stores — datasets, head instances, fine-tuned foundation models — loaded
 * together because "what do I have?" is one question, and answering it from three tabs is
 * what made cleaning up hard enough to ask for.
 *
 * Each list loads and fails **independently**. A head registry that will not read must not
 * hide the datasets, which is precisely the situation someone opens this tab in.
 */

import { useCallback, useEffect, useState } from 'react';

import { deleteDataset, listDatasets, type DatasetInfo } from '../api/datasets';
import {
  deleteFoundationInstance,
  listFoundations,
  type FoundationInfo,
} from '../api/foundation';
import {
  deleteHeadInstance,
  listHeadInstances,
  type HeadInstanceInfo,
} from '../api/headInstances';

export type LibraryKind = 'dataset' | 'head' | 'finetune';

/** One thing to delete. The kind rides along because ids are opaque and three different
 *  stores answer to them — guessing from the id is not possible and should not be. */
export interface LibraryTarget {
  readonly kind: LibraryKind;
  readonly id: string;
  readonly name: string;
}

export interface LibraryState {
  readonly datasets: readonly DatasetInfo[];
  readonly heads: readonly HeadInstanceInfo[];
  readonly finetunes: readonly FoundationInfo[];
  readonly loading: boolean;
  readonly error: string | null;
  readonly busyId: string | null;
  readonly remove: (kind: LibraryKind, id: string) => Promise<void>;
  /** Delete several at once (doc 54). Clearing eleven verification leftovers one
   *  confirmation at a time is the thing that made cleaning up not happen. */
  readonly removeMany: (targets: readonly LibraryTarget[]) => Promise<void>;
  readonly refresh: () => Promise<void>;
}

/** A catalogue entry is a *download*, managed in Admin / Models; only a model the user
 *  trained belongs here. `approx_size_mb` is 0 for an instance because nothing was
 *  downloaded for it — which is exactly what distinguishes the two. */
export function isFineTuned(entry: FoundationInfo): boolean {
  return entry.approx_size_mb === 0;
}

/** `busyId` while a bulk delete runs. A sentinel rather than null, so every row disables
 *  itself — the alternative is a list you can keep clicking while it is being rewritten. */
export const BULK = '__bulk__';

export function useLibrary(): LibraryState {
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [finetunes, setFinetunes] = useState<readonly FoundationInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    setLoading(true);
    const failures: string[] = [];

    const results = await Promise.allSettled([
      listDatasets(),
      listHeadInstances(),
      listFoundations(),
    ]);

    if (results[0].status === 'fulfilled') setDatasets(results[0].value);
    else failures.push('datasets');

    if (results[1].status === 'fulfilled') setHeads(results[1].value);
    else failures.push('heads');

    if (results[2].status === 'fulfilled') {
      setFinetunes(results[2].value.filter(isFineTuned));
    } else {
      failures.push('fine-tuned models');
    }

    // Named rather than "something went wrong": the user is here to clean up, and needs
    // to know which list is incomplete before deleting anything based on it.
    setError(failures.length === 0 ? null : `Could not load ${failures.join(' or ')}.`);
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  /** One delete, without refreshing. The callers below decide when to re-read. */
  const deleteOne = useCallback(async (kind: LibraryKind, id: string): Promise<void> => {
    if (kind === 'dataset') await deleteDataset(id);
    else if (kind === 'head') await deleteHeadInstance(id);
    else await deleteFoundationInstance(id);
  }, []);

  const removeMany = useCallback(
    async (targets: readonly LibraryTarget[]): Promise<void> => {
      if (targets.length === 0) return;
      setBusyId(BULK);
      setError(null);

      // Sequential, not Promise.all. Deleting a dataset and a head that references it at
      // the same time is a race against the store, and the failure it produces is exactly
      // the kind that leaves half a thing behind.
      const failed: string[] = [];
      for (const target of targets) {
        try {
          await deleteOne(target.kind, target.id);
        } catch {
          failed.push(target.name);
        }
      }

      // Re-read first, then report: `refresh` clears the error when every list loads, so
      // setting it before would wipe the message the user needs. Same bug as doc 51's.
      await refresh();
      if (failed.length > 0) {
        setError(
          `Could not delete ${failed.length} of ${targets.length}: ${failed.join(', ')}. ` +
            'The lists below are what is really there.',
        );
      }
      setBusyId(null);
    },
    [deleteOne, refresh],
  );

  const remove = useCallback(
    async (kind: LibraryKind, id: string): Promise<void> => {
      setBusyId(id);
      setError(null);
      try {
        await deleteOne(kind, id);
        await refresh();
      } catch {
        // Re-read rather than trusting the optimistic removal: a delete that half-failed
        // leaves the list lying about what is on disk, on the one screen that must not.
        //
        // The message is set **after** the refresh, not before. `refresh` ends by setting
        // the error to null when every list loads — so setting it first meant the user saw
        // nothing at all, and the row they had just tried to delete quietly reappeared.
        await refresh();
        setError('Could not delete that. The list below is what is really there.');
      } finally {
        setBusyId(null);
      }
    },
    [deleteOne, refresh],
  );

  return {
    datasets,
    heads,
    finetunes,
    loading,
    error,
    busyId,
    remove,
    removeMany,
    refresh,
  };
}
