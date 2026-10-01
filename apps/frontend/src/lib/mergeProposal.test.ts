import { describe, expect, it } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { mergeProposal } from './mergeProposal';

const box = (id: string, text: string, x: number, extra: Partial<CanvasBox> = {}): CanvasBox => ({
  id, label: 'positive', provenance: 'grounding-dino', x, y: 0, w: 10, h: 10, text, ...extra,
});

describe('mergeProposal (doc 119)', () => {
  it('keeps saved and hand-drawn annotations, replaces only unsaved proposals', () => {
    const current = [
      box('saved', 'm8', 0, { saved: true }),
      box('drawn', 'm9', 20, { provenance: 'hand-drawn' }),
      box('old', 'm8', 40),
    ];
    const merged = mergeProposal(current, [box('new', 'm8', 60)]);
    expect(merged.map((b) => b.id)).toEqual(['new', 'saved', 'drawn']);
  });

  it('drops a new proposal that is a kept object again', () => {
    const merged = mergeProposal([box('saved', 'm8', 0, { saved: true })], [box('again', 'M8', 1), box('other', 'm9', 1)]);
    expect(merged.map((b) => b.id)).toEqual(['other', 'saved']);
  });

  it('in a review keeps only the proposals of that class', () => {
    const merged = mergeProposal([box('saved', 'm8', 0, { saved: true })], [box('a', 'm10', 30), box('b', 'm8', 60)], 'm10');
    expect(merged.map((b) => b.id)).toEqual(['a', 'saved']);
  });
});
