/** Doc 170: the same object on the next picture gets the same decision, and only it. */

import { describe, expect, it } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { applyCorrections, recordCorrections } from './carryCorrections';

function box(over: Partial<CanvasBox> = {}): CanvasBox {
  return { id: 'b', label: 'positive', provenance: 'foundation-model', x: 100, y: 100, w: 100, h: 100, text: 'person', ...over };
}

const originals = (...boxes: CanvasBox[]): Map<string, CanvasBox> => new Map(boxes.map((b) => [b.id, b]));

describe('recordCorrections', () => {
  it('records a rename, a rejection and a removal, and nothing for an untouched proposal', () => {
    const model = originals(box({ id: 'a' }), box({ id: 'b', x: 400 }), box({ id: 'c', x: 700 }), box({ id: 'd', x: 900 }));
    const final = [box({ id: 'a', text: 'worker' }), box({ id: 'b', x: 400, label: 'negative' }), box({ id: 'd', x: 900 })];
    const recorded = recordCorrections(model, final);
    expect(recorded).toHaveLength(3);
    expect(recorded.find((c) => c.x === 100)).toMatchObject({ modelClass: 'person', text: 'worker', removed: false });
    expect(recorded.find((c) => c.x === 400)).toMatchObject({ label: 'negative', removed: false });
    expect(recorded.find((c) => c.x === 700)).toMatchObject({ removed: true });
  });

  it('keys on where the model put it, even when the user moved the box', () => {
    const [c] = recordCorrections(originals(box({ id: 'a' })), [box({ id: 'a', x: 300, text: 'worker' })]);
    expect(c?.x).toBe(100);
  });
});

describe('applyCorrections', () => {
  const renamed = recordCorrections(originals(box({ id: 'a' })), [box({ id: 'a', text: 'worker', label: 'unclear' })]);

  it('applies the decision to the same object, slightly moved', () => {
    const { boxes, counts } = applyCorrections([box({ id: 'n', x: 110, y: 105 })], renamed);
    expect(boxes[0]).toMatchObject({ id: 'n', text: 'worker', label: 'unclear', x: 110 });
    expect(counts).toEqual({ renamed: 1, verdicts: 1, removed: 0 });
  });

  it('leaves a box that moved too far, or one of another model class', () => {
    expect(applyCorrections([box({ id: 'n', x: 160 })], renamed).boxes[0]?.text).toBe('person');
    expect(applyCorrections([box({ id: 'n', text: 'car' })], renamed).boxes[0]?.text).toBe('car');
  });

  it('removes what was removed', () => {
    const gone = recordCorrections(originals(box({ id: 'a' })), []);
    const { boxes, counts } = applyCorrections([box({ id: 'n' }), box({ id: 'm', x: 500 })], gone);
    expect(boxes.map((b) => b.id)).toEqual(['m']);
    expect(counts.removed).toBe(1);
  });

  it('pairs one to one, best overlap first: two people side by side stay two', () => {
    const one = recordCorrections(originals(box({ id: 'a' })), [box({ id: 'a', label: 'negative' })]);
    const { boxes } = applyCorrections([box({ id: 'far', x: 125 }), box({ id: 'near', x: 102 })], one);
    expect(boxes.find((b) => b.id === 'near')?.label).toBe('negative');
    expect(boxes.find((b) => b.id === 'far')?.label).toBe('positive');
  });
});
