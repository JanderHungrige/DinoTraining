import { describe, expect, it } from 'vitest';

import type { ImageReview } from './generatorSave';
import { inBand, markUnclear, normaliseBand } from './unclearBand';

const BAND = { low: 0.3, high: 0.5 };

function review(scores: (number | undefined)[]): ImageReview {
  return {
    path: '/f/a.png',
    boxes: scores.map((score, i) => ({ id: `b${i}`, label: 'positive', score }) as never),
    masks: [],
    maskResponse: null,
    imageSize: { width: 1, height: 1 },
  };
}

describe('unclear band (doc 72)', () => {
  it('is inclusive at both ends', () => {
    expect(inBand(0.3, BAND)).toBe(true);
    expect(inBand(0.5, BAND)).toBe(true);
    expect(inBand(0.29, BAND)).toBe(false);
    expect(inBand(0.51, BAND)).toBe(false);
  });

  it('never asks about a proposal without a score', () => {
    expect(inBand(undefined, BAND)).toBe(false);
  });

  it('puts bounds typed the wrong way round back in order, and clamps them', () => {
    expect(normaliseBand({ low: 0.6, high: 0.2 })).toEqual({ low: 0.2, high: 0.6 });
    expect(normaliseBand({ low: -1, high: 5 })).toEqual({ low: 0, high: 1 });
  });

  it('marks only the in-band proposals unclear, and counts them', () => {
    const { review: marked, count } = markUnclear(review([0.9, 0.4, 0.1, 0.5]), BAND);
    expect(count).toBe(2);
    expect(marked.boxes.map((box) => box.label)).toEqual([
      'positive',
      'unclear',
      'positive',
      'unclear',
    ]);
  });

  it('leaves the original review untouched', () => {
    const original = review([0.4]);
    markUnclear(original, BAND);
    expect(original.boxes[0]!.label).toBe('positive');
  });

  it('marks masks the same way as boxes', () => {
    const withMask: ImageReview = {
      ...review([]),
      masks: [{ id: 'm0', label: 'positive', score: 0.35 } as never],
    };
    const { review: marked, count } = markUnclear(withMask, BAND);
    expect(count).toBe(1);
    expect(marked.masks[0]!.label).toBe('unclear');
  });
});
