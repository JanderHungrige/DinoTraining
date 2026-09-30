/**
 * "Ask me when a prediction is unclear" (doc 72): a score band the user sets, and what
 * autoplay does with the proposals that fall inside it.
 *
 * Detectors score on different scales. Grounding DINO's 0.35 is a confident box, RF-DETR's
 * is a coin toss. So the band is the user's, per run, and never a built-in notion of
 * "uncertain".
 */

import type { ImageReview } from './generatorSave';

export interface UnclearBand {
  readonly low: number;
  readonly high: number;
}

export const DEFAULT_BAND: UnclearBand = Object.freeze({ low: 0.3, high: 0.5 });

/** The band as typed, in order. Typing the bounds the wrong way round is not a reason to
 *  ask about nothing, and clamping keeps a stray 5 from meaning "everything". */
export function normaliseBand(band: UnclearBand): UnclearBand {
  const clamp = (value: number): number => Math.min(1, Math.max(0, value));
  const [low, high] = [clamp(band.low), clamp(band.high)].sort((a, b) => a - b) as [
    number,
    number,
  ];
  return { low, high };
}

/** Inclusive at both ends. A proposal with no score cannot be judged, so it never asks. */
export function inBand(score: number | undefined, band: UnclearBand): boolean {
  return score !== undefined && score >= band.low && score <= band.high;
}

/**
 * The proposals inside the band, relabelled `unclear` so they stand out and so an
 * unanswered question saves as unclear rather than as the model's guess. Returns how many
 * were marked; zero means there is nothing to ask.
 */
export function markUnclear(
  review: ImageReview,
  band: UnclearBand,
): { readonly review: ImageReview; readonly count: number } {
  let count = 0;
  const mark = <T extends { readonly score?: number; readonly label: string }>(item: T): T => {
    if (!inBand(item.score, band)) return item;
    count += 1;
    return { ...item, label: 'unclear' };
  };
  const boxes = review.boxes.map(mark);
  const masks = review.masks.map(mark);
  return { review: { ...review, boxes, masks }, count };
}
