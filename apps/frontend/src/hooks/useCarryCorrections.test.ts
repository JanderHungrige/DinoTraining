/**
 * Doc 170 in the session's order of events: proposals arrive, the user corrects them,
 * the picture changes, new proposals arrive.
 */

import { act, renderHook } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { useCarryCorrections, type CarrySession } from './useCarryCorrections';

function box(over: Partial<CanvasBox> = {}): CanvasBox {
  return { id: 'b', label: 'positive', provenance: 'foundation-model', x: 100, y: 100, w: 100, h: 100, text: 'person', ...over };
}

const SIZE = { width: 1920, height: 1080 };

function setup(enabled = true) {
  // The session's state lives in React, as in the Studio: the hook's `setBoxes` is a real
  // state setter, called from an effect.
  const view = renderHook(() => {
    const [state, setState] = useState<Omit<CarrySession, 'setBoxes'>>({ currentImage: 'f1.png', boxes: [], imageSize: SIZE });
    const setBoxes = (next: CanvasBox[]): void => setState((current) => ({ ...current, boxes: next }));
    const carried = useCarryCorrections({ ...state, setBoxes }, enabled);
    return { state, setState, carried };
  });
  const update = (over: Partial<CarrySession>): void =>
    act(() => view.result.current.setState((current) => ({ ...current, ...over })));
  return { view, update, boxes: () => view.result.current.state.boxes };
}

describe('useCarryCorrections', () => {
  it('renames and rejects on the next picture what was renamed and rejected on this one', () => {
    const { view, update, boxes } = setup();
    update({ boxes: [box({ id: 'a' }), box({ id: 'b', x: 500 })] }); // the model's proposals
    update({ boxes: [box({ id: 'a', text: 'worker' }), box({ id: 'b', x: 500, label: 'negative' })] }); // the user
    update({ currentImage: 'f2.png', boxes: [] }); // next picture
    update({ boxes: [box({ id: 'n1', x: 104 }), box({ id: 'n2', x: 495 }), box({ id: 'n3', x: 900 })] });
    expect(boxes().find((b) => b.id === 'n1')?.text).toBe('worker');
    expect(boxes().find((b) => b.id === 'n2')?.label).toBe('negative');
    expect(boxes().find((b) => b.id === 'n3')).toMatchObject({ text: 'person', label: 'positive' });
    expect(view.result.current.carried).toEqual({ renamed: 1, verdicts: 1, removed: 0 });
  });

  it('chains: an untouched carried decision goes on to the picture after', () => {
    const { update, boxes } = setup();
    update({ boxes: [box({ id: 'a' })] });
    update({ boxes: [box({ id: 'a', text: 'worker' })] });
    update({ currentImage: 'f2.png', boxes: [] });
    update({ boxes: [box({ id: 'n1', x: 104 })] });
    update({ currentImage: 'f3.png', boxes: [] });
    update({ boxes: [box({ id: 'm1', x: 108 })] });
    expect(boxes()[0]?.text).toBe('worker');
  });

  it('does nothing when switched off, or when the picture size differs', () => {
    const off = setup(false);
    off.update({ boxes: [box({ id: 'a' })] });
    off.update({ boxes: [] });
    off.update({ currentImage: 'f2.png', boxes: [] });
    off.update({ boxes: [box({ id: 'n1' })] });
    expect(off.boxes()).toHaveLength(1);

    const resized = setup();
    resized.update({ boxes: [box({ id: 'a' })] });
    resized.update({ boxes: [] });
    resized.update({ currentImage: 'f2.png', boxes: [], imageSize: { width: 640, height: 480 } });
    resized.update({ boxes: [box({ id: 'n1' })] });
    expect(resized.boxes()).toHaveLength(1);
  });

  it('never touches saved or hand-drawn annotations', () => {
    const { update, boxes } = setup();
    update({ boxes: [box({ id: 'a' })] });
    update({ boxes: [] });
    update({ currentImage: 'f2.png', boxes: [box({ id: 's', saved: true }), box({ id: 'h', provenance: 'hand-drawn' })] });
    expect(boxes().map((b) => b.id)).toEqual(['s', 'h']);
  });
});
