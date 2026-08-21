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

import { useHeadRun } from './useHeadRun';

const fetchMock = vi.fn<typeof fetch>();

const HEAD = {
  id: 'h1',
  name: 'Depth probe',
  summary: 'Depth · trained on 1 dataset',
  kind: 'trained-here',
  head_type_id: 'linear-depth',
  task: 'depth',
  render_hint: 'depth-map',
  backbone_id: 'dinov2-small',
  backbone_family: 'dinov2',
  embed_dim: 384,
  num_classes: 0,
  class_names: [],
  dataset_ids: ['d1'],
  metrics: {},
  primary_metric: null,
  primary_metric_value: null,
  epochs_trained: 3,
  best_epoch: 2,
  source_repo: null,
  created_at: '2026-08-20T00:00:00Z',
};

const FOUNDATION = {
  id: 'depth-anything-v2-small',
  title: 'Depth Anything V2 (small)',
  description: 'Monocular depth.',
  task: 'depth',
  render_hint: 'depth-map',
  model_id: 'depth-anything-v2-small',
  licence: 'Apache-2.0',
  non_commercial: false,
  installed: true,
  approx_size_mb: 95,
};

function prediction(id: string, name: string) {
  return {
    instance_id: id,
    head_name: name,
    head_type_id: id,
    task: 'depth',
    render_hint: 'depth-map',
    class_names: [],
    payload: { depth_png: 'x', min: 0, max: 1, height: 4, width: 4 },
    grid: [0, 0],
    elapsed_ms: 10,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

interface Routes {
  foundations?: readonly unknown[];
  foundationStatus?: number;
}

function route({ foundations = [FOUNDATION], foundationStatus = 200 }: Routes = {}): void {
  fetchMock.mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes('/foundation/predict')) {
      return Promise.resolve(
        foundationStatus === 200
          ? json(prediction('depth-anything-v2-small', 'Depth Anything V2 (small)'))
          : json({ error: { code: 'conflict', message: 'not installed' } }, foundationStatus),
      );
    }
    if (url.includes('/foundation')) return Promise.resolve(json({ foundations }));
    if (url.includes('/heads')) return Promise.resolve(json({ heads: [HEAD] }));
    if (url.includes('/inference/compose')) {
      return Promise.resolve(
        json({ predictions: [prediction('h1', 'Depth probe')], passes: 1, elapsed_ms: 50 }),
      );
    }
    return Promise.resolve(json({}));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

const IMAGE = '/pics/a.jpg';

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

describe('a result belongs to the image it came from', () => {
  /**
   * The bug Jan hit: run a detector on the first image of a folder, page to the next, and
   * the *first* image's boxes are still drawn — over every later image. The prediction
   * never expired, it just stopped being true. Present since Wave 3 for trained heads too;
   * only visible once someone runs a model and then pages through a folder.
   */
  it('does not show image one\'s boxes over image two', async () => {
    route();
    const { result, rerender } = renderHook(({ path }) => useHeadRun(path), {
      initialProps: { path: '/pics/a.jpg' },
    });
    await waitFor(() => expect(result.current.foundations).toHaveLength(1));

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run('/pics/a.jpg');
    });
    expect(result.current.result?.predictions).toHaveLength(1);

    rerender({ path: '/pics/b.jpg' });

    expect(result.current.result).toBeNull();
  });

  it('shows it again when you page back to that image', async () => {
    // Why the gate is derived rather than cleared on navigation: the result is still a
    // true statement about image one, so returning to image one should show it.
    route();
    const { result, rerender } = renderHook(({ path }) => useHeadRun(path), {
      initialProps: { path: '/pics/a.jpg' },
    });
    await waitFor(() => expect(result.current.foundations).toHaveLength(1));

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run('/pics/a.jpg');
    });

    rerender({ path: '/pics/b.jpg' });
    expect(result.current.result).toBeNull();

    rerender({ path: '/pics/a.jpg' });
    expect(result.current.result?.predictions).toHaveLength(1);
  });

  it('does not show a response that lands after the user has moved on', async () => {
    // The same gate covers the race for free: a slow response for image one arrives while
    // image two is on screen, and simply does not appear.
    route();
    const { result, rerender } = renderHook(({ path }) => useHeadRun(path), {
      initialProps: { path: '/pics/a.jpg' },
    });
    await waitFor(() => expect(result.current.foundations).toHaveLength(1));

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    const pending = result.current.run('/pics/a.jpg');
    rerender({ path: '/pics/b.jpg' });
    await act(async () => {
      await pending;
    });

    expect(result.current.result).toBeNull();
  });

  it('shows nothing when no image is on screen', async () => {
    route();
    const { result } = renderHook(() => useHeadRun(null));
    await waitFor(() => expect(result.current.foundations).toHaveLength(1));

    act(() => result.current.toggleFoundation('depth-anything-v2-small'));
    await act(async () => {
      await result.current.run('/pics/a.jpg');
    });

    expect(result.current.result).toBeNull();
  });
});

