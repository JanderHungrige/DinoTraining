/**
 * The annotation session: image list, current index, boxes, dirty state, counters.
 *
 * All the sequencing lives here so the tab stays presentational and the rules
 * (save-before-navigate, counts-from-the-backend) are testable without a browser.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import { EMPTY_COUNTS, saveImageBoxes, type DatasetCounts } from '../api/datasets';
import type { ImageSource } from '../components/ImageSourceField';
import { proposalFailure, proposeFor } from '../lib/proposeFor';
import { useSessionImages } from './useSessionImages';
import type { CanvasBox } from '../types/annotation';

/**
 * What proposes the boxes.
 *
 * A **discriminated union, not optional fields**, because the two modes are exclusive by
 * decision (Wave 5): choosing a head replaces the prompt rather than joining it. Optional
 * fields would make "a prompt *and* a head" representable, and every consumer would then
 * have to decide what that means — which is how a rule stops being a rule.
 */
export type ProposalSource =
  | {
      readonly kind: 'prompt';
      readonly prompt: string;
      readonly boxThreshold: number;
      readonly textThreshold: number;
    }
  | {
      readonly kind: 'head';
      readonly backboneId: string;
      readonly instanceId: string;
      readonly scoreThreshold: number;
    }
  | {
      // A general detector — no backbone to name and nothing trained. Doc 42.
      readonly kind: 'foundation';
      readonly foundationId: string;
      readonly scoreThreshold: number;
      /** What to segment, for a concept-prompted model (doc 45). Empty for a detector,
       *  which predicts its own classes whatever is typed at it. */
      readonly concept?: string;
    };

export interface SessionConfig {
  /** Where the images come from (doc 50). A dataset is a first-class source: the app
   *  already has the user's images once they have imported or generated one, and the
   *  store may have *copied* them, so the folder they remember is not where they now are. */
  readonly images: ImageSource;
  /** Where annotations are written. When the source is a dataset this is that same
   *  dataset — picking one means "carry on working on this", so its boxes load onto the
   *  canvas and edits replace them. */
  readonly datasetId: string;
  readonly source: ProposalSource;
}

export interface AnnotationSession {
  readonly images: readonly string[];
  /** Every image the source holds, ignoring any prescan filter. */
  readonly allImages: readonly string[];
  readonly filtered: boolean;
  readonly setFilter: (paths: readonly string[] | null) => void;
  readonly index: number;
  readonly currentImage: string | null;
  readonly boxes: readonly CanvasBox[];
  readonly imageSize: { width: number; height: number } | null;
  readonly counts: DatasetCounts;
  readonly dirty: boolean;
  readonly busy: boolean;
  readonly proposing: boolean;
  readonly error: string | null;
  readonly setBoxes: (boxes: CanvasBox[]) => void;
  /** The canvas reports the image's natural size on load, so a user who draws
   *  boxes without ever running the prompt can still save. */
  readonly reportImageSize: (width: number, height: number) => void;
  readonly propose: () => Promise<void>;
  readonly save: () => Promise<void>;
  readonly next: () => Promise<void>;
  readonly previous: () => Promise<void>;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useAnnotationSession(config: SessionConfig | null): AnnotationSession {
  // A prescan's hits (doc 53). Null means no filter. The **full** list stays loaded, so
  // turning the filter off costs nothing and re-reads nothing — which is what makes
  // "check every image after all" a toggle rather than a restart.
  const [filter, setFilterState] = useState<readonly string[] | null>(null);
  const [index, setIndex] = useState(0);
  const [boxes, setBoxesState] = useState<readonly CanvasBox[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [counts, setCounts] = useState<DatasetCounts>(EMPTY_COUNTS);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // Latest values for the async navigate path, which must not close over stale state.
  const stateRef = useRef({ boxes, dirty, index, imageSize });
  stateRef.current = { boxes, dirty, index, imageSize };

  const loaded = useSessionImages(config?.images ?? null, describe);
  const allImages = loaded.images;
  const existing = loaded.existing;

  const kept = filter === null ? null : new Set(filter);
  const images = kept === null ? allImages : allImages.filter((path) => kept.has(path));
  const currentImage = images[index] ?? null;

  // Reset exactly once per completed load. Depending on `allImages` instead would reset
  // on every render that produced a new array identity.
  useEffect(() => {
    setIndex(0);
    setBoxesState([...(existing.get(allImages[0] ?? '') ?? [])]);
    setDirty(false);
    setFilterState(null);
  }, [loaded.generation]);

  /** Show only these images, or all of them when given null (doc 53).
   *
   *  Resets to the first image, because keeping the index would land the user on an
   *  arbitrary one — position 7 of the filtered list is not position 7 of the full list,
   *  and nothing on screen would explain the jump. */
  const setFilter = useCallback(
    (paths: readonly string[] | null): void => {
      setFilterState(paths);
      setIndex(0);
      setBoxesState([...(existing.get((paths ?? allImages)[0] ?? '') ?? [])]);
      setImageSize(null);
      setDirty(false);
    },
    [allImages, existing],
  );

  const reportImageSize = useCallback((width: number, height: number): void => {
    setImageSize((current) =>
      current?.width === width && current.height === height ? current : { width, height },
    );
  }, []);

  const setBoxes = useCallback((next: CanvasBox[]): void => {
    setBoxesState(next);
    setDirty(true);
  }, []);

  const propose = useCallback(async (): Promise<void> => {
    if (!config || !currentImage) return;
    const { source } = config;
    setProposing(true);
    try {
      const proposed = await proposeFor(source, currentImage);
      if (!mounted.current) return;

      // Hand-drawn boxes survive a re-run: they are work the model cannot reproduce.
      const handDrawn = stateRef.current.boxes.filter((box) => box.provenance === 'hand-drawn');
      setBoxesState([...proposed.boxes, ...handDrawn]);
      setImageSize({ width: proposed.width, height: proposed.height });
      setDirty(true);
      setError(null);
    } catch (cause) {
      if (mounted.current) {
        setError(describe(cause, proposalFailure(source)));
      }
    } finally {
      if (mounted.current) setProposing(false);
    }
  }, [config, currentImage]);

  const saveAt = useCallback(
    async (imagePath: string): Promise<boolean> => {
      const size = stateRef.current.imageSize;
      if (!config || !size) return false;

      setBusy(true);
      try {
        // A reviewed image with no boxes is still saved: "nothing here" is a real
        // negative example, and skipping it would silently drop it from the dataset.
        const fresh = await saveImageBoxes(
          config.datasetId,
          {
            path: imagePath,
            width: size.width,
            height: size.height,
            // Head mode has no phrase to record. Each box carries its own class instead,
            // which `saveImageBoxes` sends as `prompt` — so the image-level fallback in
            // `replace_image_boxes` is neither needed nor a lie here. See doc 31.
            prompt: config.source.kind === 'prompt' ? config.source.prompt : null,
          },
          stateRef.current.boxes,
        );
        if (!mounted.current) return false;
        // Counts come from the backend's aggregate — a local tally drifts the first
        // time a save fails.
        setCounts(fresh);
        setDirty(false);
        setError(null);
        return true;
      } catch (cause) {
        if (mounted.current) setError(describe(cause, 'Could not save annotations.'));
        return false;
      } finally {
        if (mounted.current) setBusy(false);
      }
    },
    [config],
  );

  const save = useCallback(async (): Promise<void> => {
    if (currentImage) await saveAt(currentImage);
  }, [currentImage, saveAt]);

  const go = useCallback(
    async (delta: number): Promise<void> => {
      const target = stateRef.current.index + delta;
      if (target < 0 || target >= images.length) return;

      // Moving on saves first — losing ten minutes of labelling to a misclick is the
      // worst thing this screen can do.
      if (stateRef.current.dirty) {
        const from = images[stateRef.current.index];
        if (from && !(await saveAt(from))) return;
      }

      if (!mounted.current) return;
      setIndex(target);
      // A dataset source restores what that image already had; a folder source starts
      // blank. Both are "what is true about this image", which is why one line serves.
      setBoxesState([...(existing.get(images[target] ?? '') ?? [])]);
      setImageSize(null);
      setDirty(false);
    },
    [images, saveAt],
  );

  const next = useCallback(() => go(1), [go]);
  const previous = useCallback(() => go(-1), [go]);

  return {
    images,
    allImages,
    filtered: filter !== null,
    setFilter,
    index,
    currentImage,
    boxes,
    imageSize,
    counts,
    dirty,
    busy,
    proposing,
    // The session's own error wins: a save or propose failure is about what the user just
    // did, while a load error is about a source they have already seen fail.
    error: error ?? loaded.error,
    setBoxes,
    reportImageSize,
    propose,
    save,
    next,
    previous,
    canGoNext: index < images.length - 1,
    canGoPrevious: index > 0,
  };
}
