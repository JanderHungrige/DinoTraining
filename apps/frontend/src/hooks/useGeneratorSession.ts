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
import { proposeForGenerator, toReview } from '../lib/generatorProposal';
import { saveReview, type ImageReview } from '../lib/generatorSave';
import { useGeneratorImages } from './useGeneratorImages';
import type { GeneratorSession, MoveOptions } from '../types/generatorSession';
import type { GeneratorConfig } from '../types/generatorConfig';
import type { CanvasBox, ReviewMask } from '../types/annotation';

export type {
  ExpertConfig,
  FoundationConfig,
  GeneratorConfig,
  MaskConfig,
} from '../types/generatorConfig';

export type { GeneratorSession, MoveOptions } from '../types/generatorSession';

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useGeneratorSession(config: GeneratorConfig | null): GeneratorSession {
  const { images, allImages, filtered, setFilter: setImageFilter, loading, listError } =
    useGeneratorImages(config);
  const [index, setIndex] = useState(0);
  const [boxes, setBoxes] = useState<readonly CanvasBox[]>([]);
  const [masks, setMasks] = useState<readonly ReviewMask[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [producerName, setProducerName] = useState<string | null>(null);
  const [producerDetail, setProducerDetail] = useState<string | null>(null);
  const [proposing, setProposing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [counts, setCounts] = useState<DatasetCounts>(EMPTY_COUNTS);
  const [error, setError] = useState<string | null>(null);
  // Which image the review on screen was proposed for (doc 71). Auto-propose skips an image
  // that already has one, so stopping autoplay mid-hold does not re-propose over it.
  const [proposedFor, setProposedFor] = useState<string | null>(null);

  // The mask proposal is kept whole because saving needs the RLE, which deliberately
  // never enters the review type. Verdicts are paired back to it by index.
  const lastMaskProposal = useRef<MaskProposalResponse | null>(null);
  // What this session wrote, per image path (doc 70). Session memory only; reloading
  // stored annotations from the dataset is doc 74's job.
  const savedReviews = useRef(new Map<string, ImageReview>());

  // Guards a late response from a previous image overwriting the current one's review.
  const requestId = useRef(0);

  // A new config is a new run: nothing reviewed under the old one carries over.
  useEffect(() => {
    setIndex(0);
    setBoxes([]);
    setMasks([]);
    setImageSize(null);
    setProposedFor(null);
    savedReviews.current = new Map();
    setError(null);
  }, [config]);

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

      const review = toReview(currentImage, proposed);
      lastMaskProposal.current = proposed.maskResponse;
      setBoxes(review.boxes);
      setMasks(review.masks);
      setImageSize(review.imageSize);
      setProducerName(proposed.producerName);
      setProducerDetail(proposed.producerDetail);
      setDirty(proposed.found);
      setProposedFor(currentImage);
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
    setProposedFor(saved ? saved.path : null);
    setDirty(false);
  }, []);

  /** Jumps straight to an image, without saving the one being left (doc 71: autoplay has
   *  already saved it, or deliberately did not). */
  const goTo = useCallback(
    (target: number): void => {
      if (target < 0 || target >= images.length) return;
      requestId.current += 1;
      setProposing(false);
      setIndex(target);
      arrive(images[target]);
    },
    [images, arrive],
  );

  /** The review on screen as it stands now, edits included (doc 72: the answer to a
   *  question autoplay asked is whatever the user left on the canvas). */
  const currentReview = useCallback(
    (): ImageReview | null =>
      currentImage === null
        ? null
        : { path: currentImage, boxes, masks, maskResponse: lastMaskProposal.current, imageSize },
    [currentImage, boxes, masks, imageSize],
  );

  /** Puts a review produced elsewhere (autoplay) on screen, as if it had been proposed here. */
  const show = useCallback((review: ImageReview): void => {
    lastMaskProposal.current = review.maskResponse;
    setBoxes(review.boxes);
    setMasks(review.masks);
    setImageSize(review.imageSize);
    setProposedFor(review.path);
    setDirty(review.boxes.length > 0 || review.masks.length > 0);
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
  const setFilter = useCallback(
    (paths: readonly string[] | null): void => {
      setImageFilter(paths);
      setIndex(0);
      arrive(undefined);
    },
    [setImageFilter, arrive],
  );

  const reportImageSize = useCallback((width: number, height: number) => {
    setImageSize((current) => current ?? { width, height });
  }, []);

  return {
    images,
    allImages,
    filtered,
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
    error: error ?? listError,
    setBoxes: editBoxes,
    setMasks: editMasks,
    reportImageSize,
    propose,
    save,
    next: (options?: MoveOptions) => move(1, options),
    previous: (options?: MoveOptions) => move(-1, options),
    saved,
    goTo,
    show,
    currentReview,
    proposedFor,
    canGoNext: index < images.length - 1,
    canGoPrevious: index > 0,
  };
}
