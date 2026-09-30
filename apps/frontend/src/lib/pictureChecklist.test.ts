import { describe, expect, it } from 'vitest';

import { ENGLISH } from '../i18n';
import type { CanvasBox } from '../types/annotation';
import { checkLine } from './pictureChecklist';

function box(text: string, extra: Partial<CanvasBox> = {}): CanvasBox {
  return { id: text + Math.random(), label: 'positive', provenance: 'hand-drawn', x: 0, y: 0, w: 1, h: 1, text, ...extra };
}
const MASK = { mask: { rle: { size: [1, 1] as [number, number], counts: [0, 1] }, png: '' } };

describe('pictureChecklist (doc 104)', () => {
  it('one class per picture: met with one, explained with several', () => {
    expect(checkLine('picture-class', [box('ring'), box('Ring')], 0, [], ENGLISH)).toMatchObject({ met: true, text: 'One class: ring' });
    expect(checkLine('picture-class', [box('ring'), box('blob')], 0, [], ENGLISH).text).toBe(
      'Several classes (ring, blob): a classifier skips this picture',
    );
  });

  it('counts outlines against every object, and ignores rejected ones', () => {
    const boxes = [box('ring', MASK), box('ring'), box('ring', { label: 'negative' })];
    expect(checkLine('masks', boxes, 0, [], ENGLISH)).toMatchObject({ met: false, text: '1 of 2 have an outline' });
    expect(checkLine('masks', [box('ring', MASK)], 0, [], ENGLISH)).toMatchObject({ met: true, text: 'All 1 have an outline' });
  });

  it('lists the phrases on the picture, a class name counting as one', () => {
    expect(checkLine('phrases', [box('car', { phrases: ['car', 'red car'] }), box('Bus')], 0, [], ENGLISH).text).toBe('car, red car, bus');
  });

  it('checked per picture compares statuses with the dataset\'s phrases', () => {
    const status = { phrase_id: 1, text: 'ring', status: 'complete' as const };
    expect(checkLine('picture-status', [], 2, [status], ENGLISH)).toMatchObject({ met: false, text: 'Checked for 1 of 2 phrases' });
    expect(checkLine('picture-status', [], 1, [status], ENGLISH)).toMatchObject({ met: true, text: 'Checked for all 1 phrase' });
    expect(checkLine('picture-status', [], 0, [], ENGLISH).met).toBe(false);
  });

  it('an empty picture has nothing marked yet', () => {
    expect(checkLine('boxes', [], 0, [], ENGLISH)).toMatchObject({ met: false, text: 'Nothing marked yet' });
  });
});
