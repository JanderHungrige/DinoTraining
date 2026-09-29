/**
 * Stored masks for the frame on screen, fetched ahead of playback (doc 74).
 *
 * Only annotated frames are asked for, and each at most once: a sequence plays forwards,
 * so the next few are fetched while the current one shows, and a frame played twice is
 * served from the cache.
 */

import { useEffect, useRef, useState } from 'react';

import { listImageMasks } from '../api/datasetMasks';
import type { SequenceFrame } from '../api/datasetSequences';
import type { CanvasBox } from '../types/annotation';

const AHEAD = 6;

export function useFrameMasks(
  datasetId: string,
  frames: readonly SequenceFrame[],
  index: number,
  enabled: boolean,
): readonly CanvasBox[] {
  const cache = useRef(new Map<string, readonly CanvasBox[] | 'pending'>());
  const [, setArrived] = useState(0);

  useEffect(() => {
    cache.current = new Map();
  }, [datasetId, frames]);

  useEffect(() => {
    if (!enabled) return;
    for (const frame of frames.slice(index, index + AHEAD)) {
      if (!frame.annotated || cache.current.has(frame.path)) continue;
      cache.current.set(frame.path, 'pending');
      listImageMasks(datasetId, frame.path)
        .then((masks) => cache.current.set(frame.path, masks))
        .catch(() => cache.current.set(frame.path, []))
        .finally(() => setArrived((count) => count + 1));
    }
  }, [datasetId, frames, index, enabled]);

  const current = frames[index] ? cache.current.get(frames[index].path) : undefined;
  return Array.isArray(current) ? current : [];
}
