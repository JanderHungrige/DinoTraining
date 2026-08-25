/**
 * The class vocabulary a box can be given (doc 60).
 *
 * **Two sources, merged here rather than on the server.** The backend already unions the
 * `dataset_classes` table with the classes on stored boxes, which covers every dataset
 * that predates the table. What it cannot know is what is on the canvas *right now*: run
 * Grounding DINO with `a bolt. a nut.` and both are on screen, unsaved, and a picker that
 * cannot offer them is visibly wrong. So the caller passes the classes currently in play
 * and they are folded in as offered-but-not-stored.
 *
 * Creating goes to the server and takes the response as the new truth — the server owns
 * ordering and the case rule, and re-deriving either here would be a second implementation
 * that drifts.
 */

import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../api/client';
import {
  createDatasetClass,
  deleteDatasetClass,
  listDatasetClasses,
  type ClassInfo,
} from '../api/datasetClasses';

export interface DatasetClasses {
  /** Every class that can be chosen, sorted case-insensitively. */
  readonly names: readonly string[];
  /** The stored vocabulary, with box counts. For anything that needs more than a name. */
  readonly classes: readonly ClassInfo[];
  readonly loading: boolean;
  readonly error: string | null;
  /** Create a class and select it. Resolves to the name as stored — which may differ in
   *  case from what was typed, because the first spelling of a class wins. */
  readonly create: (name: string) => Promise<string | null>;
  readonly remove: (name: string) => Promise<void>;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

/** Case-insensitive union, first spelling wins — the same rule the store enforces. */
function merge(stored: readonly ClassInfo[], inPlay: readonly string[]): readonly string[] {
  const byKey = new Map<string, string>();
  for (const entry of stored) byKey.set(entry.name.toLowerCase(), entry.name);
  for (const name of inPlay) {
    const trimmed = name.trim();
    if (!trimmed) continue;
    const key = trimmed.toLowerCase();
    if (!byKey.has(key)) byKey.set(key, trimmed);
  }
  return [...byKey.values()].sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
}

export function useDatasetClasses(
  datasetId: string | null,
  inPlay: readonly string[] = [],
): DatasetClasses {
  const [classes, setClasses] = useState<readonly ClassInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (datasetId === null) {
      setClasses([]);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    void listDatasetClasses(datasetId, controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setClasses(found);
      })
      .catch((cause: unknown) => {
        // Non-fatal: the picker still offers whatever is on the canvas. A vocabulary that
        // fails to load must not take the review surface down with it.
        if (!controller.signal.aborted) setError(describe(cause, 'Could not load classes.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [datasetId]);

  const create = useCallback(
    async (name: string): Promise<string | null> => {
      const trimmed = name.trim();
      if (datasetId === null || !trimmed) return null;
      try {
        const updated = await createDatasetClass(datasetId, trimmed);
        setClasses(updated);
        setError(null);
        // The stored spelling, which may differ in case from what was typed. Returning
        // the typed one would select an option that is not in the list.
        return (
          updated.find((entry) => entry.name.toLowerCase() === trimmed.toLowerCase())?.name ??
          trimmed
        );
      } catch (cause) {
        setError(describe(cause, 'Could not add that class.'));
        return null;
      }
    },
    [datasetId],
  );

  const remove = useCallback(
    async (name: string): Promise<void> => {
      if (datasetId === null) return;
      try {
        setClasses(await deleteDatasetClass(datasetId, name));
        setError(null);
      } catch (cause) {
        setError(describe(cause, 'Could not remove that class.'));
      }
    },
    [datasetId],
  );

  return { names: merge(classes, inPlay), classes, loading, error, create, remove };
}
