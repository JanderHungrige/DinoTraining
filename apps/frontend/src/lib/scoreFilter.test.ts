import { describe, expect, it } from 'vitest';

import type { Prediction } from '../api/inference';
import { aboveScore, emptyBecause } from './scoreFilter';

function boxes(scores: number[]): Prediction {
  return {
    instance_id: 'h',
    head_name: 'Object detection: person +2 more',
    head_type_id: 'dense-detector',
    task: 'detection',
    render_hint: 'boxes',
    class_names: ['person', 'signal'],
    payload: { boxes: scores.map((_, i) => [i, i, 10, 10]), scores, classes: scores.map((_, i) => i % 2) },
    grid: [32, 32],
    elapsed_ms: 1,
  };
}

describe('the viewer threshold (2026-10-02)', () => {
  it('keeps the boxes at or above it, with their classes in step', () => {
    const shown = aboveScore(boxes([0.9, 0.2, 0.3, 0.29]), 0.3);
    expect(shown.payload['scores']).toEqual([0.9, 0.3]);
    expect(shown.payload['boxes']).toEqual([[0, 0, 10, 10], [2, 2, 10, 10]]);
    expect(shown.payload['classes']).toEqual([0, 0]);
  });

  it("says why a pane is empty: the head's best guess, or that it found nothing", () => {
    expect(emptyBecause(boxes([0.21, 0.05]), 0.3)).toEqual({ best: 0.21 });
    expect(emptyBecause(boxes([]), 0.3)).toEqual({ best: null });
    expect(emptyBecause(boxes([0.31]), 0.3)).toBeUndefined();
  });

  it('leaves other kinds of results alone', () => {
    const masks = { ...boxes([0.1]), render_hint: 'masks' as const };
    expect(aboveScore(masks, 0.5)).toBe(masks);
    expect(emptyBecause(masks, 0.5)).toBeUndefined();
  });
});
