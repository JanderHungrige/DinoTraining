/**
 * The dataset-generator session: image list, current index, proposed boxes, review state.
 *
 * Mirrors `useAnnotationSession`'s shape so the two review surfaces stay recognisable, but
 * it is a separate hook rather than a parameter on that one: the Studio proposes from a
 * *text prompt* and this proposes from a *trained head*, and folding both into one hook
 * would mean every caller carries the union of two configs and half of it is always null.
 *
 * There is no save here on purpose — writing reviewed proposals back is feature 7. A
 * disabled Save button would be worse than none: it reads as broken rather than absent.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { listFolderImages } from '../api/annotate';
import { ApiError } from '../api/client';
import { proposeWithExpertHead, toCanvasBoxes } from '../api/generate';
import type { CanvasBox } from '../types/annotation';

export interface GeneratorConfig {
  readonly folder: string;
  readonly backboneId: string;
  readonly instanceId: string;
  readonly scoreThreshold: number;
}

export interface GeneratorSession {
  readonly images: readonly string[];
  readonly index: number;
  readonly currentImage: string | null;
  readonly boxes: readonly CanvasBox[];
  readonly imageSize: { width: number; height: number } | null;
  readonly headName: string | null;
  readonly headSummary: string | null;
  readonly loading: boolean;
  readonly proposing: boolean;
  readonly error: string | null;
  readonly setBoxes: (boxes: CanvasBox[]) => void;
  readonly reportImageSize: (width: number, height: number) => void;
  readonly propose: () => Promise<void>;
  readonly next: () => void;
  readonly previous: () => void;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}

function describe(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useGeneratorSession(config: GeneratorConfig | null): GeneratorSession {
  const [images, setImages] = useState<readonly string[]>([]);
  const [index, setIndex] = useState(0);
  const [boxes, setBoxes] = useState<readonly CanvasBox[]>([]);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);
  const [headName, setHeadName] = useState<string | null>(null);
  const [headSummary, setHeadSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [proposing, setProposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Guards a late response from a previous image overwriting the current one's boxes.
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
      const response = await proposeWithExpertHead({
        imagePath: currentImage,
        backboneId: config.backboneId,
        instanceId: config.instanceId,
        scoreThreshold: config.scoreThreshold,
      });
      // A response for an image the user has already navigated away from must not land.
      if (ticket !== requestId.current) return;

      setBoxes(toCanvasBoxes(response));
      setImageSize({ width: response.width, height: response.height });
      setHeadName(response.head_name);
      setHeadSummary(response.head_summary);
    } catch (caught) {
      if (ticket === requestId.current) {
        setError(describe(caught, 'The head could not propose boxes for this image.'));
      }
    } finally {
      if (ticket === requestId.current) setProposing(false);
    }
  }, [config, currentImage]);

  const move = useCallback(
    (delta: number) => {
      // Invalidates any proposal still in flight for the image being left.
      requestId.current += 1;
      setIndex((current) => {
        const next = current + delta;
        if (next < 0 || next >= images.length) return current;
        setBoxes([]);
        setImageSize(null);
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
    imageSize,
    headName,
    headSummary,
    loading,
    proposing,
    error,
    setBoxes,
    reportImageSize,
    propose,
    next: () => move(1),
    previous: () => move(-1),
    canGoNext: index < images.length - 1,
    canGoPrevious: index > 0,
  };
}
