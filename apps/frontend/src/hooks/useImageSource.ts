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
import { resolveSource, type ImageSource, type SourceItem } from '../api/inference';

export interface ImageSourceState {
  readonly items: readonly SourceItem[];
  readonly index: number;
  readonly current: SourceItem | null;
  readonly kind: ImageSource['kind'] | null;
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

export function useImageSource(path: string | null): ImageSourceState {
  const [source, setSource] = useState<ImageSource | null>(null);
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

    if (!path) {
      setLoading(false);
      return;
    }

    const controller = new AbortController();
    setLoading(true);

    void (async () => {
      try {
        const resolved = await resolveSource(path, controller.signal);
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
  }, [path]);

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
