/**
 * Stepping through whatever the user pointed the viewer at.
 *
 * This is the input contract feature 19's viewer consumes: *something that yields images
 * one at a time under a stable identity*. It is deliberately not "a list of paths" — a
 * video source has to be able to satisfy this same shape later without the viewer
 * changing.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import { listDatasetImages } from '../api/datasets';
import { resolveSource, type ResolvedSource, type SourceItem } from '../api/inference';

export interface ImageSourceState {
  readonly items: readonly SourceItem[];
  readonly index: number;
  readonly current: SourceItem | null;
  readonly kind: ResolvedSource['kind'] | null;
  readonly root: string | null;
  readonly loading: boolean;
  readonly error: string | null;
  /** Resolved fine, but there was nothing in it — a message, not a failure. */
  readonly empty: boolean;
  readonly truncated: boolean;
  readonly next: () => void;
  readonly previous: () => void;
  /** Jump to an item by its identity, never by position. */
  readonly select: (itemId: string) => void;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

/** A dataset, shaped exactly as `resolveSource` shapes a folder (doc 50).
 *
 *  Built here rather than server-side because the backend route answers "what is at this
 *  path", and a dataset is not at a path — its images may be scattered originals. Same
 *  shape out, so nothing downstream learns a second kind of source. */
async function datasetAsSource(datasetId: string, signal: AbortSignal): Promise<ResolvedSource> {
  const entries = await listDatasetImages(datasetId, signal);
  return {
    kind: 'folder',
    root: datasetId,
    // A dataset listing is never capped: the store returns what it holds.
    truncated: false,
    // `item_id` is the app's stable identity for a result — never a path. A dataset's
    // stored path is already unique within it, so it serves, and prefixing keeps it
    // from ever colliding with an id the backend minted for a folder listing.
    items: entries.map((entry) => ({
      item_id: `dataset:${datasetId}:${entry.path}`,
      name: baseName(entry.path),
      path: entry.path,
    })),
  };
}

function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function useImageSource(path: string | null, dataset: string | null = null): ImageSourceState {
  const [source, setSource] = useState<ResolvedSource | null>(null);
  // Only the position is stored. The current item is derived, because seeding state from
  // data that has not arrived yet is how this codebase has produced bugs twice.
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const itemsRef = useRef<readonly SourceItem[]>([]);

  useEffect(() => {
    setSource(null);
    setIndex(0);
    setError(null);
    itemsRef.current = [];

    if (!path && !dataset) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    void (async () => {
      try {
        const resolved = dataset
          ? await datasetAsSource(dataset, controller.signal)
          : await resolveSource(path as string, controller.signal);
        if (controller.signal.aborted) return;
        setSource(resolved);
        itemsRef.current = resolved.items;
      } catch (cause) {
        if (controller.signal.aborted) return;
        setError(describe(cause, 'Could not read that path.'));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [path, dataset]);

  const items = source?.items ?? [];

  const step = useCallback((delta: number): void => {
    setIndex((current) => {
      const target = current + delta;
      // Clamped rather than wrapped: at the end of a folder, "next" doing nothing is
      // information; silently restarting at the first image is not.
      if (target < 0 || target >= itemsRef.current.length) return current;
      return target;
    });
  }, []);

  const next = useCallback(() => step(1), [step]);
  const previous = useCallback(() => step(-1), [step]);

  const select = useCallback((itemId: string): void => {
    const target = itemsRef.current.findIndex((item) => item.item_id === itemId);
    if (target >= 0) setIndex(target);
  }, []);

  return {
    items,
    index,
    current: items[index] ?? null,
    kind: source?.kind ?? null,
    root: source?.root ?? null,
    loading,
    error,
    empty: source !== null && items.length === 0,
    truncated: source?.truncated ?? false,
    next,
    previous,
    select,
    canGoNext: index < items.length - 1,
    canGoPrevious: index > 0,
  };
}
