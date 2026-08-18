/**
 * The sequencing contract feature 19's viewer consumes.
 *
 * The load sequence matters more than any single assertion here: the hook is rendered
 * with no path and then given one, which is the order a real user produces and the only
 * order that catches state seeded from data that has not arrived yet.
 */

import { renderHook, waitFor, act } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ImageSource } from '../api/inference';
import { useImageSource } from './useImageSource';

function item(name: string): { item_id: string; name: string; path: string } {
  return { item_id: `id-${name}`, name, path: `/photos/${name}` };
}

function source(overrides: Partial<ImageSource> = {}): ImageSource {
  return {
    kind: 'folder',
    root: '/photos',
    items: [item('a.png'), item('b.png'), item('c.png')],
    truncated: false,
    ...overrides,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(() => Promise.resolve(json(source())));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useImageSource', () => {
  it('holds nothing until a path is given', async () => {
    const { result } = renderHook(() => useImageSource(null));

    expect(result.current.items).toHaveLength(0);
    expect(result.current.current).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('selects the first item once the source arrives', async () => {
    const { result, rerender } = renderHook(
      ({ path }: { path: string | null }) => useImageSource(path),
      { initialProps: { path: null as string | null } },
    );

    rerender({ path: '/photos' });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.items).toHaveLength(3);
    expect(result.current.current?.name).toBe('a.png');
    expect(result.current.index).toBe(0);
  });

  it('steps forward and back without running off either end', async () => {
    const { result } = renderHook(() => useImageSource('/photos'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.canGoPrevious).toBe(false);
    act(() => result.current.previous());
    expect(result.current.index).toBe(0);

    act(() => result.current.next());
    expect(result.current.current?.name).toBe('b.png');
    act(() => result.current.next());
    expect(result.current.canGoNext).toBe(false);
    act(() => result.current.next());
    expect(result.current.index).toBe(2);
  });

  it('selects by item id, not by position', async () => {
    const { result } = renderHook(() => useImageSource('/photos'));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.select('id-c.png'));

    expect(result.current.current?.name).toBe('c.png');
  });

  it('resets to the first item when the path changes', async () => {
    const { result, rerender } = renderHook(({ path }: { path: string }) => useImageSource(path), {
      initialProps: { path: '/photos' },
    });
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.next());
    expect(result.current.index).toBe(1);

    fetchMock.mockImplementation(() =>
      Promise.resolve(json(source({ root: '/other', items: [item('z.png')] }))),
    );
    rerender({ path: '/other' });

    await waitFor(() => expect(result.current.current?.name).toBe('z.png'));
    expect(result.current.index).toBe(0);
  });

  it('reports an empty folder as a message rather than an error', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(json(source({ items: [] }))));

    const { result } = renderHook(() => useImageSource('/photos'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.current).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.empty).toBe(true);
  });

  it('surfaces a backend failure instead of showing an empty source', async () => {
    fetchMock.mockImplementation(() =>
      Promise.resolve(json({ error: { code: 'not_found', message: 'Not a folder: /nope' } }, 404)),
    );

    const { result } = renderHook(() => useImageSource('/nope'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('Not a folder: /nope');
    expect(result.current.empty).toBe(false);
  });

  it('says when a folder was truncated', async () => {
    fetchMock.mockImplementation(() => Promise.resolve(json(source({ truncated: true }))));

    const { result } = renderHook(() => useImageSource('/photos'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.truncated).toBe(true);
  });
});
