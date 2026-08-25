/**
 * Choosing heads — and foundation models — and running them over the current image.
 *
 * A **foundation model** (doc 37) predicts on its own: no backbone, no head, no shared
 * pass. It is therefore selected separately and run separately, and the two result sets are
 * merged into one `ComposedResult`. Merging rather than keeping two lists is the point of
 * the wave: the viewer's panes, the overlay registry and the compare layout already work
 * off `Prediction[]` and must not learn that some predictions came from elsewhere.
 *
 * **A result belongs to the image it was computed from.** `currentPath` is required for
 * that reason: without it this hook happily returned image 1's boxes over image 2, 3 and 4
 * as the user paged through a folder — the prediction never expired, it just stopped being
 * true. Gating is *derived* rather than cleared on navigation, which is what makes paging
 * back to an earlier image correctly show that image's own result again, and what makes a
 * response arriving after the user has moved on simply not appear.
 *
 * The backbone is **derived from the selection** rather than picked separately. A head
 * only runs against the backbone it was registered for (doc 18 refuses the request
 * otherwise), so a separate backbone control would let the user build an invalid
 * combination and only learn about it from a 409. Here the first selected head fixes the
 * backbone and the rest are marked incompatible while it stands.
 */

import { useCallback, useMemo, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import type { HeadTask } from '../api/heads';
import { runFoundation, type FoundationInfo } from '../api/foundation';
import type { HeadInstanceInfo } from '../api/headInstances';
import { runHeads, type ComposedResult } from '../api/inference';
import { useRunnableModels } from './useRunnableModels';

export interface HeadRunState {
  readonly heads: readonly HeadInstanceInfo[];
  readonly selected: readonly string[];
  /** Self-contained models, offered alongside the heads. Installed ones only. */
  readonly foundations: readonly FoundationInfo[];
  readonly selectedFoundations: readonly string[];
  readonly toggleFoundation: (foundationId: string) => void;
  /** What a concept segmenter should look for (doc 45). One field for all of them:
   *  two concept models selected at once with *different* concepts is a nicety this
   *  surface does not need, and per-model state to express it. */
  readonly concept: string;
  readonly setConcept: (concept: string) => void;
  /** Fixed by the first selected head; null when nothing is selected. */
  readonly backboneId: string | null;
  /** Narrows the offered list. Same-task comparison is this filter, not a mode. */
  readonly taskFilter: HeadTask | null;
  /** Show only heads trained on this dataset (doc 52). Null means all. */
  readonly datasetFilter: string | null;
  /** Every dataset any installed head was trained on, id -> name, for the picker.
   *  Built from the datasets that actually appear, so a filter can never offer a
   *  choice that matches nothing. */
  readonly trainedOn: readonly { readonly id: string; readonly name: string }[];
  /** The task the current selection is on, when they all share one. */
  readonly selectedTask: HeadTask | null;
  readonly running: boolean;
  readonly result: ComposedResult | null;
  readonly error: string | null;
  readonly loadingHeads: boolean;
  readonly toggle: (instanceId: string) => void;
  readonly setTaskFilter: (task: HeadTask | null) => void;
  readonly setDatasetFilter: (datasetId: string | null) => void;
  readonly clear: () => void;
  readonly run: (imagePath: string) => Promise<void>;
  /** True when this head cannot join the current selection — different backbone. */
  readonly isIncompatible: (head: HeadInstanceInfo) => boolean;
}

function describe(cause: unknown, fallback: string): string {
  return cause instanceof ApiError ? cause.message : fallback;
}

export function useHeadRun(currentPath: string | null): HeadRunState {
  // What exists, versus what the user chose to do with it. See `useRunnableModels`.
  const catalogue = useRunnableModels();
  const { heads, foundations, trainedOn, loadingHeads } = catalogue;

  const [selected, setSelected] = useState<readonly string[]>([]);
  const [selectedFoundations, setSelectedFoundations] = useState<readonly string[]>([]);
  const [concept, setConcept] = useState('');
  const [result, setResult] = useState<ComposedResult | null>(null);
  /** Which image `result` describes. Null whenever there is no result. */
  const [resultPath, setResultPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [taskFilter, setTaskFilterState] = useState<HeadTask | null>(null);
  const [datasetFilter, setDatasetFilterState] = useState<string | null>(null);

  const inFlight = useRef<AbortController | null>(null);

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

  const setDatasetFilter = useCallback((datasetId: string | null): void => {
    setDatasetFilterState(datasetId);
  }, []);

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

  /**
   * Wrapped rather than passed through, for the same reason `toggle` clears the result:
   * a mask still on screen under a *changed* concept reads as though the new phrase had
   * been segmented. Asking for "sky" and being shown the previous answer is the exact
   * complaint this fix came from.
   */
  const changeConcept = useCallback((next: string): void => {
    setConcept(next);
    setResult(null);
  }, []);

  const toggleFoundation = useCallback((foundationId: string): void => {
    setSelectedFoundations((current) =>
      current.includes(foundationId)
        ? current.filter((id) => id !== foundationId)
        : [...current, foundationId],
    );
    setResult(null);
  }, []);

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
    setSelectedFoundations([]);
    setResult(null);
    setResultPath(null);
    setError(null);
  }, []);

  const run = useCallback(
    async (imagePath: string): Promise<void> => {
      // A foundation-only run is legitimate — it needs no backbone at all. Requiring one
      // here is what would make "compare a foundation model against nothing" impossible,
      // and it is also the most likely first thing a user does after installing one.
      const hasHeads = selected.length > 0 && backboneId !== null;
      if (!hasHeads && selectedFoundations.length === 0) return;

      // Clicking Run twice, or switching image mid-run, must not race two responses
      // into the same pane — the slower one would win and show the wrong image's result.
      inFlight.current?.abort();
      const controller = new AbortController();
      inFlight.current = controller;

      setRunning(true);
      setError(null);
      try {
        // Started together rather than in sequence: they share nothing, so serialising
        // them would add the depth model's second onto the heads' for no reason.
        const [composed, foundationResults] = await Promise.all([
          hasHeads && backboneId
            ? runHeads({ imagePath, backboneId, instanceIds: selected }, controller.signal)
            : Promise.resolve(null),
          Promise.all(
            selectedFoundations.map((foundationId) =>
              runFoundation(
                { imagePath, foundationId, ...(concept ? { concept } : {}) },
                controller.signal,
              ),
            ),
          ),
        ]);
        if (controller.signal.aborted) return;

        setResultPath(imagePath);
        setResult({
          predictions: [...(composed?.predictions ?? []), ...foundationResults],
          // Foundation models run their own forward; they are not backbone passes and
          // are deliberately not counted as such, or the "two framings, seven heads"
          // number stops meaning what doc 18 measured.
          passes: composed?.passes ?? 0,
          elapsed_ms: Math.max(
            composed?.elapsed_ms ?? 0,
            ...foundationResults.map((prediction) => prediction.elapsed_ms),
            0,
          ),
        });
      } catch (cause) {
        if (controller.signal.aborted) return;
        setError(describe(cause, 'Could not run that selection.'));
        setResult(null);
        setResultPath(null);
      } finally {
        if (!controller.signal.aborted) setRunning(false);
      }
    },
    // `concept` belongs here. Without it `run` was frozen at whatever the concept was
    // when the *selection* last changed — and since the concept field only appears once
    // a concept model is ticked, that was always the empty string. Every Grounded SAM and
    // SAM 3 run went out with no concept at all, came back as an all-background mask, and
    // looked identical however the phrase was changed.
    [selected, backboneId, selectedFoundations, concept],
  );

  // Derived, not stored: a result is shown only while the image it describes is the one
  // on screen. Clearing on navigation instead would lose a result the user could page
  // back to, and would still race a response that lands after they have moved on.
  const resultForCurrentImage = resultPath !== null && resultPath === currentPath ? result : null;

  return {
    heads,
    selected,
    foundations,
    concept,
    setConcept: changeConcept,
    selectedFoundations,
    toggleFoundation,
    backboneId,
    taskFilter,
    datasetFilter,
    trainedOn,
    selectedTask,
    running,
    result: resultForCurrentImage,
    // A run failure is about what the user just did and wins over a catalogue failure,
    // which is about a list they have already seen come up empty.
    error: error ?? catalogue.error,
    loadingHeads,
    toggle,
    setTaskFilter,
    setDatasetFilter,
    clear,
    run,
    isIncompatible,
  };
}
