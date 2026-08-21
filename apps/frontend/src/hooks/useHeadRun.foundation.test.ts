/**
 * Running a foundation model beside the heads (doc 37).
 *
 * The wave's demo-state is *comparing* a foundation depth model against a trained one on
 * the same image, so the assertions here are about the two result sets arriving as **one**
 * list of predictions. If they stayed separate, every consumer downstream — the panes, the
 * overlay registry, the compare layout — would need to learn that some predictions come
 * from somewhere else, which is exactly what the shared `Prediction` shape avoids.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FOUNDATION, HEAD, IMAGE, fetchMock, json, route } from './headRun.testkit';
import { useHeadRun } from './useHeadRun';

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

async function ready(path: string = IMAGE) {
  const { result } = renderHook(() => useHeadRun(path));
  await waitFor(() => expect(result.current.heads).toHaveLength(1));
  await waitFor(() => expect(result.current.foundations).toHaveLength(1));
  return result;
}

describe('offering foundation models', () => {
  it('lists them alongside the heads', async () => {
    route();
    const result = await ready();
    expect(result.current.foundations[0]?.id).toBe('depth-anything-v2-small');
  });

  it('offers only installed ones', async () => {
    // An uninstalled model in the runner offers an action whose only outcome is a 409
    // telling you to go to the admin panel. The admin panel is where you install it.
    route({ foundations: [{ ...FOUNDATION, installed: false }] });
    const { result } = renderHook(() => useHeadRun(IMAGE));
    await waitFor(() => expect(result.current.heads).toHaveLength(1));
    expect(result.current.foundations).toEqual([]);
  });

  it('survives the foundation listing failing', async () => {
    // Non-fatal by design: heads must still run if this endpoint is unhappy.
    fetchMock.mockImplementation((input: unknown) => {
      const url = String(input);
      if (url.includes('/foundation')) return Promise.resolve(json({ bad: true }, 500));
      if (url.includes('/heads')) return Promise.resolve(json({ heads: [HEAD] }));
      return Promise.resolve(json({}));
    });
    const { result } = renderHook(() => useHeadRun(IMAGE));
    await waitFor(() => expect(result.current.heads).toHaveLength(1));
    expect(result.current.foundations).toEqual([]);
    expect(result.current.error).toBeNull();
  });
});

describe('running them', () => {
  it('runs a foundation model with no head selected', async () => {
    // It needs no backbone, so requiring one would make this — the most likely first
    // thing anyone does after installing one — silently impossible.
    route();
    const result = await ready();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run(IMAGE);
    });

    expect(result.current.result?.predictions).toHaveLength(1);
    expect(result.current.result?.predictions[0]?.head_name).toBe('Depth Anything V2 (small)');
  });

  it('merges head and foundation predictions into one list', async () => {
    route();
    const result = await ready();

    act(() => result.current.toggle('h1'));
    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run(IMAGE);
    });

    const names = result.current.result?.predictions.map((p) => p.head_name);
    expect(names).toEqual(['Depth probe', 'Depth Anything V2 (small)']);
  });

  it('does not count a foundation run as a backbone pass', async () => {
    // `passes` measures shared backbone forwards — doc 18's "two framings, seven heads".
    // A foundation model runs its own forward and is not one of them.
    route();
    const result = await ready();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run(IMAGE);
    });

    expect(result.current.result?.passes).toBe(0);
  });

  it('does nothing when neither a head nor a foundation model is chosen', async () => {
    route();
    const result = await ready();

    await act(async () => {
      await result.current.run(IMAGE);
    });

    expect(result.current.result).toBeNull();
  });

  it('surfaces a failed foundation run as an error, not a partial result', async () => {
    route({ foundationStatus: 409 });
    const result = await ready();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run(IMAGE);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.result).toBeNull();
  });

  it('clears foundation selection along with the heads', async () => {
    route();
    const result = await ready();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    act(() => result.current.clear());

    expect(result.current.selectedFoundations).toEqual([]);
  });

  it('drops a stale result when the foundation selection changes', async () => {
    route();
    const result = await ready();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run(IMAGE);
    });
    expect(result.current.result).not.toBeNull();

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    expect(result.current.result).toBeNull();
  });
});
