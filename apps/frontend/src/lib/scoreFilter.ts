/**
 * Detections shown above a threshold the user sets, filtered in the browser (2026-10-02).
 *
 * The Inference Viewer asks the backend for every candidate (threshold 0; it returns at
 * most 50 per head) and filters here, so moving the slider is instant and a head that finds
 * nothing above the threshold can still say what its best guess was. Jan's report: a head
 * with mAP 0.007 showed an empty picture with no word as to why.
 */

import type { Prediction } from '../api/inference';

export const DEFAULT_MIN_SCORE = 0.3;

function isBoxes(prediction: Prediction): boolean {
  return prediction.render_hint === 'boxes' && Array.isArray(prediction.payload['scores']);
}

/** The prediction with only the boxes at or above `minScore`; other kinds unchanged. */
export function aboveScore(prediction: Prediction, minScore: number): Prediction {
  if (!isBoxes(prediction)) return prediction;
  const scores = prediction.payload['scores'] as readonly number[];
  const keep = scores.map((score, index) => (score >= minScore ? index : -1)).filter((index) => index >= 0);
  const pick = (key: string): unknown[] => {
    const values = prediction.payload[key];
    return Array.isArray(values) ? keep.map((index) => values[index]) : [];
  };
  return { ...prediction, payload: { ...prediction.payload, boxes: pick('boxes'), scores: pick('scores'), classes: pick('classes') } };
}

/** For a boxes prediction with nothing at or above `minScore`: its best score (null when it
 *  found nothing at all). Undefined when there is nothing to explain. */
export function emptyBecause(prediction: Prediction, minScore: number): { best: number | null } | undefined {
  if (!isBoxes(prediction)) return undefined;
  const scores = prediction.payload['scores'] as readonly number[];
  if (scores.some((score) => score >= minScore)) return undefined;
  return { best: scores.length ? Math.max(...scores) : null };
}
