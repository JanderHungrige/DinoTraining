/**
 * A result belongs to the image it was computed from (doc 21's stale-result bug).
 *
 * Split from `useHeadRun.foundation.test.ts` at the project's 300-line gate. These stay
 * together because they are one idea tested from four directions.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchMock, route } from './headRun.testkit';
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

