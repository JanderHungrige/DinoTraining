/**
 * The dataset-generator session: image list, current index, proposals, review state.
 *
 * Three ways to propose; the config union lives in `types/generatorConfig.ts`.
 *
 * Doc 70: `propose` returns what it proposed and `save` takes an explicit review, so
 * autoplay can save what it has just proposed without waiting on a render. The session also
 * remembers what it saved per image, so going back shows the saved review rather than a
 * blank canvas that auto-propose would fill and auto-save would then write over.
 */

import { useCallback, useEffect, useRef, useState } from 'react';


import { ApiError } from '../api/client';
import { EMPTY_COUNTS, type DatasetCounts } from '../api/datasets';
import type { MaskProposalResponse } from '../api/generate';
import { proposeForGenerator } from '../lib/generatorProposal';
import { saveReview, type ImageReview } from '../lib/generatorSave';
import type { GeneratorConfig } from '../types/generatorConfig';
import { resolveImageSource, sourceNoun } from '../lib/imageSource';
import type { CanvasBox, ReviewMask } from '../types/annotation';

export type {
  ExpertConfig,
  FoundationConfig,
  GeneratorConfig,
  MaskConfig,
} from '../types/generatorConfig';

export interface MoveOptions {
  readonly autoSave?: boolean;
}

export interface GeneratorSession {
  readonly images: readonly string[];
  /** Every image the source holds, ignoring any prescan filter. */
  readonly allImages: readonly string[];
  readonly filtered: boolean;
  readonly setFilter: (paths: readonly string[] | null) => void;
  readonly index: number;
  readonly currentImage: string | null;
  readonly boxes: readonly CanvasBox[];
  readonly masks: readonly ReviewMask[];
  readonly imageSize: { width: number; height: number } | null;
  /** What produced the current proposals — a head's name, or an annotator's. */
  readonly producerName: string | null;
  readonly producerDetail: string | null;
  readonly loading: boolean;
  readonly proposing: boolean;
  readonly saving: boolean;
  /** True when there is something reviewed that has not been written yet. */
  readonly dirty: boolean;
  readonly counts: DatasetCounts;
  readonly error: string | null;
  readonly setBoxes: (boxes: CanvasBox[]) => void;
  readonly setMasks: (masks: ReviewMask[]) => void;
  readonly reportImageSize: (width: number, height: number) => void;
  /** Resolves to what was proposed, or null when it failed or the image changed meanwhile. */
  readonly propose: () => Promise<ImageReview | null>;
  /** Saves the given review, or the one on screen. False when the save failed. */
  readonly save: (review?: ImageReview) => Promise<boolean>;
  /** Moves on, saving a dirty image first when asked. False when that save failed and the
   *  session stayed where it was, so the review is not lost. */
  readonly next: (options?: MoveOptions) => Promise<boolean>;
  readonly previous: (options?: MoveOptions) => Promise<boolean>;
  /** What this session saved for an image, if anything. */
  readonly saved: (path: string) => ImageReview | undefined;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useGeneratorSession(config: GeneratorConfig | null): GeneratorSession {
  const [allImages, setImages] = useState<readonly string[]>([]);
  // A prescan's hits (doc 53). Null means no filter. The full list stays loaded, so
  // turning the filter off costs nothing and re-reads nothing.
  const [filter, setFilterState] = useState<readonly string[] | null>(null);
  const [index, setIndex] = useState(0);
  const [boxes, setBoxes] = useState<readonly CanvasBox[]>([]);
  const [masks, setMasks] = useState<readonly ReviewMask[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [producerName, setProducerName] = useState<string | null>(null);
  const [producerDetail, setProducerDetail] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [counts, setCounts] = useState<DatasetCounts>(EMPTY_COUNTS);
  const [error, setError] = useState<string | null>(null);

  // The mask proposal is kept whole because saving needs the RLE, which deliberately
  // never enters the review type. Verdicts are paired back to it by index.
  const lastMaskProposal = useRef<MaskProposalResponse | null>(null);
  // What this session wrote, per image path (doc 70). Session memory only; reloading
  // stored annotations from the dataset is doc 74's job.
  const savedReviews = useRef(new Map<string, ImageReview>());

  // Guards a late response from a previous image overwriting the current one's review.
  const requestId = useRef(0);

  useEffect(() => {
    if (!config) {
      setImages([]);
      setIndex(0);
      return;
    }
    const controller = new AbortController();
    // Cleared before the new listing is asked for, not after it arrives (doc 50, bug 1). A source
    // that fails to load must not leave the previous one's images on screen: they render
    // fully interactive, so the user reviews the old folder's pictures while the boxes
    // save into the newly chosen dataset, with only an error message to say otherwise.
    setImages([]);
    setIndex(0);
    setBoxes([]);
    setMasks([]);
    setImageSize(null);
    setFilterState(null);
    savedReviews.current = new Map();
    setLoading(true);
    setError(null);

    resolveImageSource(config.images, controller.signal)
      .then((found) => {
        setImages(found);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setError(describe(caught, `Could not list that ${sourceNoun(config.images)}.`));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [config]);

  const kept = filter === null ? null : new Set(filter);
  const images = kept === null ? allImages : allImages.filter((path) => kept.has(path));
  const currentImage = images[index] ?? null;

  const propose = useCallback(async (): Promise<ImageReview | null> => {
    if (!config || !currentImage) return null;
    const ticket = ++requestId.current;

    setProposing(true);
    setError(null);
    try {
      const proposed = await proposeForGenerator(config, currentImage);
      // A response for an image the user has already navigated away from must not land:
      // its boxes and masks are in that image's coordinate space and would look plausible
      // here. The ticket stays in the hook precisely so this check cannot be extracted.
      if (ticket !== requestId.current) return null;

      const review: ImageReview = {
        path: currentImage,
        boxes: proposed.boxes,
        masks: proposed.masks,
        maskResponse: proposed.maskResponse,
        imageSize: { width: proposed.width, height: proposed.height },
      };
      lastMaskProposal.current = proposed.maskResponse;
      setBoxes(review.boxes);
      setMasks(review.masks);
      setImageSize(review.imageSize);
      setProducerName(proposed.producerName);
      setProducerDetail(proposed.producerDetail);
      setDirty(proposed.found);
      return review;
    } catch (caught) {
      if (ticket === requestId.current) {
        setError(describe(caught, 'Nothing could be proposed for this image.'));
      }
      return null;
    } finally {
      if (ticket === requestId.current) setProposing(false);
    }
  }, [config, currentImage]);

  const save = useCallback(
    async (explicit?: ImageReview): Promise<boolean> => {
      if (!config) return false;
      const review: ImageReview | null =
        explicit ??
        (currentImage
          ? { path: currentImage, boxes, masks, maskResponse: lastMaskProposal.current, imageSize }
          : null);
      if (!review) return false;

      setSaving(true);
      setError(null);
      try {
        setCounts(await saveReview(config, review));
        savedReviews.current.set(review.path, review);
        if (review.path === currentImage) setDirty(false);
        return true;
      } catch (caught) {
        setError(
          caught instanceof Error && !(caught instanceof ApiError)
            ? caught.message
            : describe(caught, 'Could not save to the dataset.'),
        );
        return false;
      } finally {
        setSaving(false);
      }
    },
    [config, currentImage, imageSize, boxes, masks],
  );

  // A hand edit is a review: drawing a box the model missed, rejecting one it found, or
  // relabelling one. Before doc 70 only a proposal with results set `dirty`, so a box drawn
  // on an image where the model found nothing could never be saved.
  const editBoxes = useCallback((next: CanvasBox[]) => {
    setBoxes(next);
    setDirty(true);
  }, []);
  const editMasks = useCallback((next: ReviewMask[]) => {
    setMasks(next);
    setDirty(true);
  }, []);

  // Stable, so effects that ask it (auto-propose) do not re-run on every render.
  const saved = useCallback((path: string) => savedReviews.current.get(path), []);

  /** Shows an image: what this session saved for it, or a clean slate. */
  const arrive = useCallback((path: string | undefined): void => {
    const saved = path === undefined ? undefined : savedReviews.current.get(path);
    setBoxes(saved?.boxes ?? []);
    setMasks(saved?.masks ?? []);
    setImageSize(saved?.imageSize ?? null);
    lastMaskProposal.current = saved?.maskResponse ?? null;
    setDirty(false);
  }, []);

  const move = useCallback(
    async (delta: number, options: MoveOptions = {}): Promise<boolean> => {
      const target = index + delta;
      if (target < 0 || target >= images.length) return false;
      // Leaving is the one moment auto-save cannot catch a correction half-made (doc 70).
      if (options.autoSave && dirty && !(await save())) return false;
      // Invalidates any proposal still in flight for the image being left.
      requestId.current += 1;
      setProposing(false);
      setIndex(target);
      arrive(images[target]);
      return true;
    },
    [index, images, dirty, save, arrive],
  );

  /** Show only these images, or all of them when given null (doc 53).
   *
   *  Resets to the first, because position 7 of the filtered list is not position 7 of the
   *  full one and nothing on screen would explain the jump. */
  const setFilter = useCallback((paths: readonly string[] | null): void => {
    setFilterState(paths);
    setIndex(0);
    setBoxes([]);
    setMasks([]);
    setImageSize(null);
  }, []);

  const reportImageSize = useCallback((width: number, height: number) => {
    setImageSize((current) => current ?? { width, height });
  }, []);

  return {
    images,
    allImages,
    filtered: filter !== null,
    setFilter,
    index,
    currentImage,
    boxes,
    masks,
    imageSize,
    producerName,
    producerDetail,
    loading,
    proposing,
    saving,
    dirty,
    counts,
    error,
    setBoxes: editBoxes,
    setMasks: editMasks,
    reportImageSize,
    propose,
    save,
    next: (options?: MoveOptions) => move(1, options),
    previous: (options?: MoveOptions) => move(-1, options),
    saved,
    canGoNext: index < images.length - 1,
    canGoPrevious: index > 0,
  };
}
