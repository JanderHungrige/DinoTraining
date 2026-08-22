/** Session start and proposal behaviour. Saving and navigation live in the sibling file. */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CONFIG, box, json, route } from './session.testkit';
import { useAnnotationSession, type SessionConfig } from './useAnnotationSession';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('session start', () => {
  it('lists the folder and starts at the first image', async () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(CONFIG));

    await waitFor(() => expect(result.current.images).toHaveLength(3));
    expect(result.current.index).toBe(0);
    expect(result.current.currentImage).toBe('/pics/a.jpg');
  });

  it('does nothing without a config', () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(null));

    expect(result.current.images).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('reports an empty folder rather than looking broken', async () => {
    route(fetchMock, { folder: () => json({ folder: '/pics', images: [] }) });
    const { result } = renderHook(() => useAnnotationSession(CONFIG));

    await waitFor(() => expect(result.current.error).toMatch(/no images/i));
  });

  it('surfaces a folder error', async () => {
    route(fetchMock, {
      folder: () => json({ error: { code: 'not_found', message: 'Not a folder' } }, 404),
    });
    const { result } = renderHook(() => useAnnotationSession(CONFIG));

    await waitFor(() => expect(result.current.error).toBe('Not a folder'));
  });

  it('lists the folder once, not per navigation', async () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(3));

    act(() => result.current.reportImageSize(200, 100));
    await act(async () => {
      await result.current.next();
    });

    const listCalls = fetchMock.mock.calls.filter(([url]) =>
      String(url).includes('/annotate/folder'),
    );
    expect(listCalls).toHaveLength(1);
  });
});

describe('proposing', () => {
  it('keeps hand-drawn boxes across a re-run', async () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(3));

    act(() => result.current.setBoxes([box({ id: 'mine', provenance: 'hand-drawn' })]));
    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.boxes.map((b) => b.provenance)).toContain('grounding-dino');
    expect(result.current.boxes.some((b) => b.id === 'mine')).toBe(true);
  });

  it('drops previous proposals on a re-run', async () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(3));

    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.boxes.filter((b) => b.provenance === 'grounding-dino')).toHaveLength(1);
  });

  it('records the image size from the response', async () => {
    route(fetchMock);
    const { result } = renderHook(() => useAnnotationSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(3));

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.imageSize).toEqual({ width: 200, height: 100 });
  });

  it('surfaces an uninstalled-model error', async () => {
    route(fetchMock, {
      annotate: () =>
        json(
          { error: { code: 'not_found', message: 'not installed. Download it in the Admin tab.' } },
          404,
        ),
    });
    const { result } = renderHook(() => useAnnotationSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(3));

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.error).toMatch(/admin tab/i);
  });
});

describe('switching to a source that fails', () => {
  /**
   * The bug Jan reported as "the image is always the same" (doc 50, bug 1).
   *
   * The images were replaced only on a *successful* load, so a folder that could not be
   * read left the previous session's pictures on screen — rendering fully interactive,
   * with only an error message above them. The user annotates the old folder's images
   * while the boxes save into the newly chosen dataset, and nothing says so.
   */
  const SECOND: SessionConfig = {
    ...CONFIG,
    images: { kind: 'folder', folder: '/other' },
    datasetId: 'ds2',
  };

  it('does not keep showing the previous source images', async () => {
    route(fetchMock);
    const { result, rerender } = renderHook(
      ({ config }: { config: SessionConfig }) => useAnnotationSession(config),
      { initialProps: { config: CONFIG } },
    );
    await waitFor(() => expect(result.current.images.length).toBeGreaterThan(0));

    route(fetchMock, {
      folder: () => json({ error: { code: 'not_found', message: 'Not a folder' } }, 404),
    });
    rerender({ config: SECOND });

    await waitFor(() => expect(result.current.error).toBeTruthy());
    expect(result.current.images).toEqual([]);
    expect(result.current.currentImage).toBeNull();
  });

  it('clears them before the new listing arrives, not after', async () => {
    // The window between asking and answering is the one the user annotates in.
    route(fetchMock);
    const { result, rerender } = renderHook(
      ({ config }: { config: SessionConfig }) => useAnnotationSession(config),
      { initialProps: { config: CONFIG } },
    );
    await waitFor(() => expect(result.current.currentImage).toBeTruthy());

    const held: { release?: () => void } = {};
    route(fetchMock, {
      folder: () =>
        new Promise<Response>((resolve) => {
          held.release = () => resolve(json({ folder: '/other', images: ['/other/a.jpg'] }));
        }) as unknown as Response,
    });
    rerender({ config: SECOND });

    await waitFor(() => expect(result.current.loadingImages).toBe(true));
    expect(result.current.currentImage).toBeNull();

    held.release?.();
    await waitFor(() => expect(result.current.currentImage).toBe('/other/a.jpg'));
  });
});
