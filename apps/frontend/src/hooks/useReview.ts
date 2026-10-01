/**
 * Review for one class (doc 119): the pictures saved before it (doc 117) become the
 * Studio's picture filter, and the proposer is asked for that class alone.
 */

import { useCallback, useState } from 'react';

import { setPictureStatus, unknownPictures } from '../api/phrases';
import type { AnnotationSession } from './useAnnotationSession';

export interface Review {
  /** The class under review, or null. */
  readonly className: string | null;
  readonly total: number;
  readonly error: string;
  readonly start: (className: string) => Promise<void>;
  readonly end: () => void;
  /** "No m10 here": an explicit `absent` for this picture, then on to the next. */
  readonly notHere: () => Promise<void>;
}

export function useReview(datasetId: string | null, session: AnnotationSession): Review {
  const [className, setClassName] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const { setFilter, currentImage, next } = session;

  const start = useCallback(
    async (name: string): Promise<void> => {
      if (datasetId === null) return;
      try {
        const paths = await unknownPictures(datasetId, name);
        setFilter(paths);
        setTotal(paths.length);
        setClassName(name);
        setError('');
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
      }
    },
    [datasetId, setFilter],
  );

  const end = useCallback((): void => {
    setFilter(null);
    setClassName(null);
  }, [setFilter]);

  const notHere = useCallback(async (): Promise<void> => {
    if (datasetId === null || className === null || currentImage === null) return;
    try {
      await setPictureStatus(datasetId, currentImage, className, 'absent');
      setError('');
      await next();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }, [datasetId, className, currentImage, next]);

  return { className, total, error, start, end, notHere };
}
