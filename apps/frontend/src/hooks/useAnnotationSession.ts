/**
 * The annotation session: image list, current index, boxes, dirty state, counters.
 *
 * All the sequencing lives here so the tab stays presentational and the rules
 * (save-before-navigate, counts-from-the-backend) are testable without a browser.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { listFolderImages, proposeBoxes, toCanvasBoxes } from '../api/annotate';
import {
  proposeWithExpertHead,
  toCanvasBoxes as expertBoxes,
} from '../api/generate';
import { ApiError } from '../api/client';
import { EMPTY_COUNTS, saveImageBoxes, type DatasetCounts } from '../api/datasets';
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
    };

export interface SessionConfig {
  readonly folder: string;
  readonly datasetId: string;
  readonly source: ProposalSource;
}

export interface AnnotationSession {
  readonly images: readonly string[];
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
  const [images, setImages] = useState<readonly string[]>([]);
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

  const currentImage = images[index] ?? null;

  // The folder is listed once per folder; re-listing on every navigation would put
  // a disk read behind the arrow keys.
  useEffect(() => {
    if (!config) return;
    const controller = new AbortController();

    void (async () => {
      try {
        const found = await listFolderImages(config.folder, controller.signal);
        if (!mounted.current) return;
        setImages(found);
        setIndex(0);
        setBoxesState([]);
        setDirty(false);
        setError(found.length === 0 ? 'No images found in that folder.' : null);
      } catch (cause) {
        if (mounted.current) setError(describe(cause, 'Could not read that folder.'));
      }
    })();

    return () => controller.abort();
  }, [config?.folder]);

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
      // Both branches return proposals already in *source* pixel coordinates and already
      // carrying their own provenance, so nothing downstream branches on mode again.
      const proposed =
        source.kind === 'head'
          ? await proposeWithExpertHead({
              imagePath: currentImage,
              backboneId: source.backboneId,
              instanceId: source.instanceId,
              scoreThreshold: source.scoreThreshold,
            }).then((response) => ({
              boxes: expertBoxes(response),
              width: response.width,
              height: response.height,
            }))
          : await proposeBoxes({
              imagePath: currentImage,
              prompt: source.prompt,
              boxThreshold: source.boxThreshold,
              textThreshold: source.textThreshold,
            }).then((response) => ({
              boxes: toCanvasBoxes(response),
              width: response.width,
              height: response.height,
            }));
      if (!mounted.current) return;

      // Hand-drawn boxes survive a re-run: they are work the model cannot reproduce.
      const handDrawn = stateRef.current.boxes.filter((box) => box.provenance === 'hand-drawn');
      setBoxesState([...proposed.boxes, ...handDrawn]);
      setImageSize({ width: proposed.width, height: proposed.height });
      setDirty(true);
      setError(null);
    } catch (cause) {
      if (mounted.current) {
        setError(
          describe(
            cause,
            source.kind === 'head' ? 'Could not run that head.' : 'Could not run the detector.',
          ),
        );
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
      setBoxesState([]);
      setImageSize(null);
      setDirty(false);
    },
    [images, saveAt],
  );

  const next = useCallback(() => go(1), [go]);
  const previous = useCallback(() => go(-1), [go]);

  return {
    images,
    index,
    currentImage,
    boxes,
    imageSize,
    counts,
    dirty,
    busy,
    proposing,
    error,
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
