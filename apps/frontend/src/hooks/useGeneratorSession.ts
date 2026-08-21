/**
 * The dataset-generator session: image list, current index, proposals, review state.
 *
 * Two ways to propose, and the config is a **discriminated union** rather than one object
 * with half its fields null. An expert head needs a backbone and an instance; a mask
 * annotator needs a concept and an annotator id, and neither set is meaningful to the
 * other. A single flat shape would make every reader check which half is populated.
 *
 * There is no save here on purpose — writing reviewed proposals back is feature 8. A
 * disabled Save button would read as broken rather than absent.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { listFolderImages } from '../api/annotate';
import { ApiError } from '../api/client';
import { EMPTY_COUNTS, saveImageBoxes, saveImageMasks, type DatasetCounts } from '../api/datasets';
import {
  proposeMasks,
  proposeWithExpertHead,
  toCanvasBoxes,
  toReviewMasks,
  type MaskProposalResponse,
} from '../api/generate';
import {
  foundationCanvasBoxes,
  proposeWithFoundation,
} from '../api/foundation';
import type { CanvasBox, ReviewMask } from '../types/annotation';

export interface ExpertConfig {
  readonly kind: 'expert';
  readonly datasetId: string;
  readonly folder: string;
  readonly backboneId: string;
  readonly instanceId: string;
  readonly scoreThreshold: number;
}

export interface MaskConfig {
  readonly kind: 'masks';
  readonly datasetId: string;
  readonly folder: string;
  readonly annotatorId: string;
  readonly concept: string;
  readonly scoreThreshold: number;
}

export interface FoundationConfig {
  readonly kind: 'foundation';
  readonly datasetId: string;
  readonly folder: string;
  /** Catalogue id of an installed detector. No backbone: it brings its own. */
  readonly foundationId: string;
  readonly scoreThreshold: number;
}

export type GeneratorConfig = ExpertConfig | MaskConfig | FoundationConfig;

export interface GeneratorSession {
  readonly images: readonly string[];
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
  readonly propose: () => Promise<void>;
  readonly save: () => Promise<void>;
  readonly next: () => void;
  readonly previous: () => void;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

async function saveMasks(
  datasetId: string,
  proposal: MaskProposalResponse | null,
  reviewed: readonly ReviewMask[],
): Promise<DatasetCounts> {
  if (!proposal) {
    // Reachable by pressing Save before proposing anything. Refusing beats inventing an
    // empty proposal, which would wipe whatever the image already had stored.
    throw new Error('Propose masks before saving.');
  }
  return saveImageMasks(datasetId, proposal, reviewed);
}

export function useGeneratorSession(config: GeneratorConfig | null): GeneratorSession {
  const [images, setImages] = useState<readonly string[]>([]);
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

  // Guards a late response from a previous image overwriting the current one's review.
  const requestId = useRef(0);

  useEffect(() => {
    if (!config) {
      setImages([]);
      setIndex(0);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    listFolderImages(config.folder, controller.signal)
      .then((found) => {
        setImages(found);
        setIndex(0);
        setBoxes([]);
        setMasks([]);
        setImageSize(null);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setError(describe(caught, 'Could not list that folder.'));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [config]);

  const currentImage = images[index] ?? null;

  const propose = useCallback(async (): Promise<void> => {
    if (!config || !currentImage) return;
    const ticket = ++requestId.current;

    setProposing(true);
    setError(null);
    try {
      if (config.kind === 'foundation') {
        const response = await proposeWithFoundation({
          imagePath: currentImage,
          foundationId: config.foundationId,
          scoreThreshold: config.scoreThreshold,
        });
        if (ticket !== requestId.current) return;

        setBoxes(foundationCanvasBoxes(response));
        setImageSize({ width: response.width, height: response.height });
        setProducerName(response.model_name);
        setProducerDetail(response.model_summary);
        setDirty(response.boxes.length > 0);
      } else if (config.kind === 'expert') {
        const response = await proposeWithExpertHead({
          imagePath: currentImage,
          backboneId: config.backboneId,
          instanceId: config.instanceId,
          scoreThreshold: config.scoreThreshold,
        });
        if (ticket !== requestId.current) return;

        setBoxes(toCanvasBoxes(response));
        setImageSize({ width: response.width, height: response.height });
        setProducerName(response.head_name);
        setProducerDetail(response.head_summary);
        setDirty(response.boxes.length > 0);
      } else {
        const response = await proposeMasks({
          imagePath: currentImage,
          concept: config.concept,
          annotatorId: config.annotatorId,
          threshold: config.scoreThreshold,
        });
        // A response for an image the user has already navigated away from must not land:
        // its masks are in that image's coordinate space and would look plausible here.
        if (ticket !== requestId.current) return;

        lastMaskProposal.current = response;
        setMasks(toReviewMasks(response));
        setImageSize({ width: response.width, height: response.height });
        setProducerName(response.annotator_name);
        setDirty(response.masks.length > 0);
        setProducerDetail(`${response.masks.length} mask(s) for “${config.concept}”`);
      }
    } catch (caught) {
      if (ticket === requestId.current) {
        setError(describe(caught, 'Nothing could be proposed for this image.'));
      }
    } finally {
      if (ticket === requestId.current) setProposing(false);
    }
  }, [config, currentImage]);

  const save = useCallback(async (): Promise<void> => {
    if (!config || !currentImage || !imageSize) return;

    setSaving(true);
    setError(null);
    try {
      const next =
        config.kind === 'masks'
          ? await saveMasks(config.datasetId, lastMaskProposal.current, masks)
          : await saveImageBoxes(
              config.datasetId,
              { path: currentImage, width: imageSize.width, height: imageSize.height },
              boxes,
            );
      setCounts(next);
      setDirty(false);
    } catch (caught) {
      setError(describe(caught, 'Could not save to the dataset.'));
    } finally {
      setSaving(false);
    }
  }, [config, currentImage, imageSize, boxes, masks]);

  const move = useCallback(
    (delta: number) => {
      // Invalidates any proposal still in flight for the image being left.
      requestId.current += 1;
      setIndex((current) => {
        const next = current + delta;
        if (next < 0 || next >= images.length) return current;
        setBoxes([]);
        setMasks([]);
        setImageSize(null);
        setDirty(false);
        lastMaskProposal.current = null;
        return next;
      });
    },
    [images.length],
  );

  const reportImageSize = useCallback((width: number, height: number) => {
    setImageSize((current) => current ?? { width, height });
  }, []);

  return {
    images,
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
    setBoxes,
    setMasks,
    reportImageSize,
    propose,
    save,
    next: () => move(1),
    previous: () => move(-1),
    canGoNext: index < images.length - 1,
    canGoPrevious: index > 0,
  };
}
