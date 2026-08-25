/**
 * The class vocabulary a picker offers (doc 60).
 *
 * The interesting property is the **merge**. The server already unions its table with the
 * classes on stored boxes; what it cannot know is what is on the canvas right now. A
 * proposal run's classes are on screen and unsaved, so a picker that could not offer them
 * would be visibly wrong about what the image contains.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useDatasetClasses } from './useDatasetClasses';

const fetchMock = vi.fn<typeof fetch>();

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function stored(...names: string[]) {
  return { classes: names.map((name) => ({ name, boxes: 1, stored: true })) };
}

/** Bodies POSTed to the classes endpoint, in order. */
const posted: string[] = [];

function route(body: unknown, status = 200, onPost?: (name: string) => unknown): void {
  fetchMock.mockImplementation((_input: unknown, init?: RequestInit) => {
    if (init?.method === 'POST') {
      const name = String(
        (JSON.parse(String(init.body ?? '{}')) as { name?: string }).name ?? '',
      );
      posted.push(name);
      return Promise.resolve(json(onPost ? onPost(name) : body, 201));
    }
    return Promise.resolve(json(body, status));
  });
}

beforeEach(() => {
  posted.length = 0;
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe('the vocabulary', () => {
  it('is empty with no dataset and asks the backend nothing', () => {
    route(stored());
    const { result } = renderHook(() => useDatasetClasses(null, []));

    expect(result.current.names).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('lists what the dataset has', async () => {
    route(stored('person', 'dog'));
    const { result } = renderHook(() => useDatasetClasses('d1', []));

    await waitFor(() => expect(result.current.names).toHaveLength(2));
    expect(result.current.names).toEqual(['dog', 'person']);
  });

  it('folds in classes that are on the canvas but not yet saved', async () => {
    route(stored('person'));
    const { result } = renderHook(() => useDatasetClasses('d1', ['a bolt', 'a nut']));

    await waitFor(() => expect(result.current.names).toHaveLength(3));
    expect(result.current.names).toEqual(['a bolt', 'a nut', 'person']);
  });

  it('treats a case-only difference as the same class, stored spelling winning', async () => {
    // Two entries differing only in case is a data-entry accident, never an intent.
    route(stored('Person'));
    const { result } = renderHook(() => useDatasetClasses('d1', ['person']));

    // Waiting on the *value*, not the length: the in-play class alone already makes the
    // list one long, so a length check passes before the vocabulary has even arrived.
    await waitFor(() => expect(result.current.names).toEqual(['Person']));
  });

  it('ignores blank classes on the canvas', async () => {
    route(stored('person'));
    const { result } = renderHook(() => useDatasetClasses('d1', ['', '  ']));

    await waitFor(() => expect(result.current.names).toEqual(['person']));
  });

  it('sorts case-insensitively', async () => {
    route(stored('Zebra', 'apple'));
    const { result } = renderHook(() => useDatasetClasses('d1', []));

    await waitFor(() => expect(result.current.names).toHaveLength(2));
    expect(result.current.names).toEqual(['apple', 'Zebra']);
  });

  it('reloads when the dataset changes', async () => {
    route(stored('person'));
    const { result, rerender } = renderHook(
      ({ id }: { id: string }) => useDatasetClasses(id, []),
      { initialProps: { id: 'd1' } },
    );
    await waitFor(() => expect(result.current.names).toEqual(['person']));

    route(stored('signal'));
    rerender({ id: 'd2' });

    await waitFor(() => expect(result.current.names).toEqual(['signal']));
  });
});

describe('when the vocabulary cannot be loaded', () => {
  it('still offers what is on the canvas', async () => {
    // Non-fatal by design: a failed listing must not take the review surface down, and
    // the classes on screen are true whatever the server said.
    route({ error: { code: 'oops', message: 'no' } }, 500);
    const { result } = renderHook(() => useDatasetClasses('d1', ['a bolt']));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.names).toEqual(['a bolt']);
  });
});

describe('creating a class', () => {
  it('sends the name and takes the response as the new vocabulary', async () => {
    route(stored('person'), 200, () => stored('person', 'signal'));
    const { result } = renderHook(() => useDatasetClasses('d1', []));
    await waitFor(() => expect(result.current.names).toEqual(['person']));

    await act(async () => {
      await result.current.create('signal');
    });

    expect(posted).toEqual(['signal']);
    expect(result.current.names).toEqual(['person', 'signal']);
  });

  it('resolves to the stored spelling, not the typed one', async () => {
    // The first spelling wins server-side. Returning the typed one would have the picker
    // select an option that is not in the list.
    route(stored('Signal'), 200, () => stored('Signal'));
    const { result } = renderHook(() => useDatasetClasses('d1', []));
    await waitFor(() => expect(result.current.names).toEqual(['Signal']));

    let created: string | null = null;
    await act(async () => {
      created = await result.current.create('signal');
    });

    expect(created).toBe('Signal');
  });

  it('trims before sending', async () => {
    route(stored(), 200, () => stored('signal'));
    const { result } = renderHook(() => useDatasetClasses('d1', []));
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.create('  signal  ');
    });

    expect(posted).toEqual(['signal']);
  });

  it('sends nothing for a blank name', async () => {
    route(stored());
    const { result } = renderHook(() => useDatasetClasses('d1', []));
    await waitFor(() => expect(result.current.loading).toBe(false));

    let created: string | null = 'x';
    await act(async () => {
      created = await result.current.create('   ');
    });

    expect(created).toBeNull();
    expect(posted).toEqual([]);
  });

  it('reports a failure and creates nothing', async () => {
    fetchMock.mockImplementation((_input: unknown, init?: RequestInit) =>
      Promise.resolve(
        init?.method === 'POST'
          ? json({ error: { code: 'unprocessable', message: 'bad name' } }, 422)
          : json(stored('person')),
      ),
    );
    const { result } = renderHook(() => useDatasetClasses('d1', []));
    await waitFor(() => expect(result.current.names).toEqual(['person']));

    let created: string | null = 'x';
    await act(async () => {
      created = await result.current.create('!!');
    });

    expect(created).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.names).toEqual(['person']);
  });
});
