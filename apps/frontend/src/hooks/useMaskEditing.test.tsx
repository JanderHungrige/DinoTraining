import { act, renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EditedMask } from '../api/segment';
import type { CanvasBox } from '../types/annotation';
import { useMaskEditing } from './useMaskEditing';

vi.mock('../api/segment', () => ({ refineOutline: vi.fn(), strokeOutline: vi.fn(), outlinesFromBoxes: vi.fn() }));
const api = await import('../api/segment');

const edited = (x: number): EditedMask => ({ rle: { size: [10, 10], counts: [x, 1] }, mask_png: `png${x}`, x, y: 1, w: 2, h: 3, score: 0.9 });
const BOX: CanvasBox = { id: 'b1', label: 'positive', provenance: 'hand-drawn', x: 10, y: 10, w: 40, h: 20, text: 'car' };

function setup(boxes: CanvasBox[] = [BOX]) {
  let current = boxes;
  const setBoxes = vi.fn((next: CanvasBox[]) => {
    current = next;
  });
  const hook = renderHook(({ list }) => useMaskEditing('/p.png', list, setBoxes, 'b1'), { initialProps: { list: current } });
  const sync = (): void => hook.rerender({ list: current });
  return { hook, setBoxes, sync, get boxes() { return current; } };
}

beforeEach(() => vi.clearAllMocks());

describe('useMaskEditing (doc 106)', () => {
  it('⊕ on a box without an outline makes one, from the box and the click', async () => {
    vi.mocked(api.refineOutline).mockResolvedValue(edited(5));
    const t = setup();
    act(() => t.hook.result.current.setTool('add'));
    act(() => t.hook.result.current.click(20, 15));
    await waitFor(() => expect(t.setBoxes).toHaveBeenCalled());
    expect(api.refineOutline).toHaveBeenCalledWith('/p.png', { x: 10, y: 10, w: 40, h: 20 }, [{ x: 20, y: 15, positive: true }]);
    expect(t.boxes[0]).toMatchObject({ id: 'b1', text: 'car', x: 5, mask: { png: 'png5' } });
  });

  it('keeps prompting from the original box as clicks accumulate, ⊖ included', async () => {
    vi.mocked(api.refineOutline).mockResolvedValue(edited(5));
    const t = setup();
    act(() => t.hook.result.current.setTool('add'));
    act(() => t.hook.result.current.click(20, 15));
    await waitFor(() => expect(t.setBoxes).toHaveBeenCalledTimes(1));
    t.sync();
    act(() => t.hook.result.current.setTool('remove'));
    act(() => t.hook.result.current.click(40, 15));
    await waitFor(() => expect(api.refineOutline).toHaveBeenCalledTimes(2));
    expect(vi.mocked(api.refineOutline).mock.calls[1]).toEqual([
      '/p.png',
      { x: 10, y: 10, w: 40, h: 20 },
      [{ x: 20, y: 15, positive: true }, { x: 40, y: 15, positive: false }],
    ]);
  });

  it('undo puts the box back as it was', async () => {
    vi.mocked(api.refineOutline).mockResolvedValue(edited(5));
    const t = setup();
    act(() => t.hook.result.current.setTool('add'));
    act(() => t.hook.result.current.click(20, 15));
    await waitFor(() => expect(t.hook.result.current.busy).toBe(false));
    t.sync();
    expect(t.hook.result.current.canUndo).toBe(true);
    act(() => t.hook.result.current.undo());
    expect(t.boxes[0]).toEqual(BOX);
  });

  it('the brush needs an outline, and says so', () => {
    const t = setup();
    act(() => t.hook.result.current.setTool('brush'));
    act(() => t.hook.result.current.stroke([[1, 1]]));
    expect(t.hook.result.current.error).toMatch(/Make an outline first/);
    expect(api.strokeOutline).not.toHaveBeenCalled();
  });

  it('outlines every positive box without one, and leaves the rest', async () => {
    const rejected: CanvasBox = { ...BOX, id: 'b2', label: 'negative' };
    vi.mocked(api.outlinesFromBoxes).mockResolvedValue([edited(7)]);
    const t = setup([BOX, rejected]);
    expect(t.hook.result.current.unoutlined).toBe(1);
    act(() => t.hook.result.current.outlineAll());
    await waitFor(() => expect(t.setBoxes).toHaveBeenCalled());
    expect(t.boxes[0]!.mask?.png).toBe('png7');
    expect(t.boxes[1]).toEqual(rejected);
  });

  it('a refusal from the server is shown, not thrown', async () => {
    vi.mocked(api.refineOutline).mockRejectedValue(new Error('sam2.1-hiera-small is not installed.'));
    const t = setup();
    act(() => t.hook.result.current.setTool('add'));
    act(() => t.hook.result.current.click(20, 15));
    await waitFor(() => expect(t.hook.result.current.error).toBe('sam2.1-hiera-small is not installed.'));
  });
});
