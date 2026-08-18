/**
 * Choosing heads and running them over the current image.
 *
 * The backbone is **derived from the selection** rather than picked separately. A head
 * only runs against the backbone it was registered for (doc 18 refuses the request
 * otherwise), so a separate backbone control would let the user build an invalid
 * combination and only learn about it from a 409. Here the first selected head fixes the
 * backbone and the rest are marked incompatible while it stands.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import type { HeadTask } from '../api/heads';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';
import { runHeads, type ComposedResult } from '../api/inference';

export interface HeadRunState {
  readonly heads: readonly HeadInstanceInfo[];
  readonly selected: readonly string[];
  /** Fixed by the first selected head; null when nothing is selected. */
  readonly backboneId: string | null;
  /** Narrows the offered list. Same-task comparison is this filter, not a mode. */
  readonly taskFilter: HeadTask | null;
  /** The task the current selection is on, when they all share one. */
  readonly selectedTask: HeadTask | null;
  readonly running: boolean;
  readonly result: ComposedResult | null;
  readonly error: string | null;
  readonly loadingHeads: boolean;
  readonly toggle: (instanceId: string) => void;
  readonly setTaskFilter: (task: HeadTask | null) => void;
  readonly clear: () => void;
  readonly run: (imagePath: string) => Promise<void>;
  /** True when this head cannot join the current selection — different backbone. */
  readonly isIncompatible: (head: HeadInstanceInfo) => boolean;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

export function useHeadRun(): HeadRunState {
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [selected, setSelected] = useState<readonly string[]>([]);
  const [result, setResult] = useState<ComposedResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingHeads, setLoadingHeads] = useState(true);
  const [taskFilter, setTaskFilterState] = useState<HeadTask | null>(null);

  const inFlight = useRef<AbortController | null>(null);

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

  const backboneId = useMemo(() => {
    const first = heads.find((head) => head.id === selected[0]);
    return first?.backbone_id ?? null;
  }, [heads, selected]);

  const selectedTask = useMemo(() => {
    const tasks = new Set(
      selected
        .map((id) => heads.find((head) => head.id === id)?.task)
        .filter((task): task is HeadTask => task !== undefined),
    );
    // Only meaningful when they agree — a mixed selection is a legitimate thing to ask
    // for, it just is not a *comparison*.
    return tasks.size === 1 ? [...tasks][0] ?? null : null;
  }, [heads, selected]);

  const setTaskFilter = useCallback((task: HeadTask | null): void => {
    setTaskFilterState(task);
    // The selection is deliberately kept. Filtering changes what is *offered*, not what
    // was chosen — silently dropping a head the user picked because they narrowed the
    // list would lose work with no way to tell it happened.
  }, []);

  const isIncompatible = useCallback(
    (head: HeadInstanceInfo): boolean =>
      backboneId !== null && head.backbone_id !== backboneId,
    [backboneId],
  );

  const toggle = useCallback((instanceId: string): void => {
    setSelected((current) =>
      current.includes(instanceId)
        ? current.filter((id) => id !== instanceId)
        : [...current, instanceId],
    );
    // A stale result under a changed selection reads as though the new heads had run.
    setResult(null);
  }, []);

  const clear = useCallback((): void => {
    setSelected([]);
    setResult(null);
    setError(null);
  }, []);

  const run = useCallback(
    async (imagePath: string): Promise<void> => {
      if (selected.length === 0 || !backboneId) return;

      // Clicking Run twice, or switching image mid-run, must not race two responses
      // into the same pane — the slower one would win and show the wrong image's result.
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;

      setRunning(true);
      setError(null);
      try {
        const composed = await runHeads(
          { imagePath, backboneId, instanceIds: selected },
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setResult(composed);
      } catch (cause) {
        if (controller.signal.aborted) return;
        setError(describe(cause, 'Could not run those heads.'));
        setResult(null);
      } finally {
        if (!controller.signal.aborted) setRunning(false);
      }
    },
    [selected, backboneId],
  );

  return {
    heads,
    selected,
    backboneId,
    taskFilter,
    selectedTask,
    running,
    result,
    error,
    loadingHeads,
    toggle,
    setTaskFilter,
    clear,
    run,
    isIncompatible,
  };
}
