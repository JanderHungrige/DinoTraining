/**
 * Loading the current image's stored masks into a review session (doc 61).
 *
 * Extracted from `useAnnotationSession` because that file sits against the project's
 * 300-line gate, and the seam is a real one: this answers "what has already been segmented
 * in this picture", and everything left there is navigation, dirty state and saving.
 *
 * **Per image**, not with the dataset listing. An RLE is a run list over the whole frame —
 * roughly 15 KB as JSON for a 2464x1600 mask — and a 392-image dataset would make the
 * listing enormous to answer a question about one picture. See `api/datasetMasks.ts`.
 *
 * The masks arrive as `CanvasBox`es and are **merged into the one array** rather than kept
 * beside it, so the numbering, the threshold, the verdict buttons and the class picker all
 * keep working on a single list and none of them learns that some annotations came from a
 * different table.
 */

import { useEffect, useRef } from 'react';

import { listImageMasks } from '../api/datasetMasks';
import type { CanvasBox } from '../types/annotation';

export interface StoredMasksOptions {
  readonly datasetId: string | null;
  readonly imagePath: string | null;
  /** Read at resolution time, not at call time — see `onLoaded`. */
  readonly isDirty: () => boolean;
  /** Called once per image that has masks, with the masks to merge in. */
  readonly onLoaded: (masks: readonly CanvasBox[]) => void;
}

export function useStoredMasks({
  datasetId,
  imagePath,
  isDirty,
  onLoaded,
}: StoredMasksOptions): void {
  // Which image's masks have already been merged. Without it a second resolution for the
  // same image — an effect re-run, a StrictMode double-mount — appends them twice.
  const mergedFor = useRef<string | null>(null);
  // Latest callbacks, so the effect can depend on the image alone. Depending on the
  // callbacks would re-fetch on every render of the component that defines them.
  const latest = useRef({ isDirty, onLoaded });
  latest.current = { isDirty, onLoaded };

  useEffect(() => {
    if (!datasetId || !imagePath) return;
    if (mergedFor.current === imagePath) return;

    const controller = new AbortController();
    void listImageMasks(datasetId, imagePath, controller.signal)
      .then((masks) => {
        if (controller.signal.aborted) return;
        mergedFor.current = imagePath;
        if (masks.length === 0) return;
        // Only while nothing has been edited. A load landing after the reviewer has
        // started work would put annotations under their hands, and one landing after a
        // re-run would restore exactly what that run replaced.
        if (latest.current.isDirty()) return;
        latest.current.onLoaded(masks);
      })
      .catch(() => {
        // Non-fatal. The boxes are already on screen, and a failed mask read must not take
        // the review surface down with them.
      });
    return () => controller.abort();
  }, [datasetId, imagePath]);

  // Navigating to another image must let its masks load, including navigating *back*.
  useEffect(() => {
    if (mergedFor.current !== imagePath) mergedFor.current = null;
  }, [imagePath]);
}
