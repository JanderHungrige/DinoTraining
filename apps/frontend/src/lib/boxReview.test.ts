/**
 * Ordering, numbering and threshold rules (doc 47).
 *
 * Each of these fails silently when wrong: a bad paint order makes a box unclickable, bad
 * numbering makes the list disagree with the image, and a bad threshold makes the user's
 * own hand-drawn work vanish. Nothing throws, so nothing but a test notices.
 */

import { describe, expect, it } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { hasScores, hiddenByThreshold, inPaintOrder, numbered, verdictCounts } from './boxReview';

function box(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return {
    id,
    label: 'positive',
    provenance: 'grounding-dino',
    x: 0,
    y: 0,
    w: 10,
    h: 10,
    ...over,
  };
}

describe('numbering', () => {
  it('is 1-based', () => {
    expect(numbered([box('a'), box('b')]).map((n) => n.number)).toEqual([1, 2]);
  });

  it('follows the list order, not the paint order', () => {
    // The number is how a person says "that one" out loud. Numbering by paint order would
    // renumber every box the moment one was resized.
    const small = box('small', { w: 5, h: 5 });
    const large = box('large', { w: 100, h: 100 });
    const items = numbered([small, large]);
    expect(items.map((n) => [n.box.id, n.number])).toEqual([
      ['small', 1],
      ['large', 2],
    ]);
    expect(inPaintOrder(items).map((n) => n.number)).toEqual([2, 1]);
  });
});

describe('paint order', () => {
  it('puts the smallest box on top', () => {
    // The reported bug: a box covered by a larger one could not be clicked. Every box is a
    // button filling its rect, so the one painted last wins the click.
    const items = numbered([
      box('big', { w: 100, h: 100 }),
      box('small', { w: 4, h: 4 }),
      box('mid', { w: 40, h: 40 }),
    ]);
    expect(inPaintOrder(items).map((n) => n.box.id)).toEqual(['big', 'mid', 'small']);
  });

  it('orders by area, not by width alone', () => {
    const wide = box('wide', { w: 100, h: 1 });
    const square = box('square', { w: 20, h: 20 });
    expect(inPaintOrder(numbered([wide, square])).map((n) => n.box.id)).toEqual([
      'square',
      'wide',
    ]);
  });

  it('leaves equal boxes in their original order', () => {
    const items = numbered([box('a'), box('b'), box('c')]);
    expect(inPaintOrder(items).map((n) => n.box.id)).toEqual(['a', 'b', 'c']);
  });

  it('does not mutate the input', () => {
    const items = numbered([box('big', { w: 99, h: 99 }), box('small', { w: 1, h: 1 })]);
    inPaintOrder(items);
    expect(items.map((n) => n.box.id)).toEqual(['big', 'small']);
  });

  it('survives a degenerate box', () => {
    const items = numbered([box('zero', { w: 0, h: 0 }), box('neg', { w: -5, h: 10 })]);
    expect(inPaintOrder(items)).toHaveLength(2);
  });
});

describe('the threshold', () => {
  it('hides a box below it', () => {
    const hidden = hiddenByThreshold([box('a', { score: 0.2 })], 0.5);
    expect([...hidden]).toEqual(['a']);
  });

  it('keeps a box exactly at it', () => {
    expect(hiddenByThreshold([box('a', { score: 0.5 })], 0.5).size).toBe(0);
  });

  it('never hides a box with no score', () => {
    // Hand-drawn boxes and imported ones carry no score. Treating that as 0 would make the
    // user's own work vanish as they dragged the slider — and the next save would drop it.
    const hidden = hiddenByThreshold([box('hand', { provenance: 'hand-drawn' })], 0.9);
    expect(hidden.size).toBe(0);
  });

  it('hides nothing at zero', () => {
    expect(hiddenByThreshold([box('a', { score: 0.01 })], 0).size).toBe(0);
  });

  it('knows when a slider would be meaningless', () => {
    expect(hasScores([box('hand')])).toBe(false);
    expect(hasScores([box('hand'), box('found', { score: 0.4 })])).toBe(true);
  });
});

describe('verdict counts', () => {
  it('counts each label', () => {
    const counts = verdictCounts([
      box('a'),
      box('b', { label: 'negative' }),
      box('c', { label: 'unclear' }),
      box('d'),
    ]);
    expect(counts).toEqual({ positive: 2, negative: 1, unclear: 1 });
  });

  it('reports zeroes rather than missing keys', () => {
    expect(verdictCounts([])).toEqual({ positive: 0, negative: 0, unclear: 0 });
  });
});
