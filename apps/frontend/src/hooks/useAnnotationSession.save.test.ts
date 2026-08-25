/** Saving and navigation — the rules that protect the user's work. */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CONFIG, COUNTS, box, json, route } from './session.testkit';
import { useAnnotationSession } from './useAnnotationSession';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function startedSession(handlers = {}) {
  route(fetchMock, handlers);
  const { result } = renderHook(() => useAnnotationSession(CONFIG));
  await waitFor(() => expect(result.current.images).toHaveLength(3));
  act(() => result.current.reportImageSize(200, 100));
  return result;
}

/**
 * The **boxes** PUT specifically.
 *
 * A save is two requests since doc 61 — masks to `/images/masks`, boxes to `/images` — so
 * "the first PUT" stopped identifying anything. Naming the endpoint is also what makes the
 * split assertable rather than incidental.
 */
function putBody(): { boxes: unknown[]; path: string; width: number } {
  return JSON.parse(String(putTo('/images')?.[1]?.body));
}

function maskBody(): { masks: unknown[]; path: string } {
  return JSON.parse(String(putTo('/images/masks')?.[1]?.body));
}

function putTo(suffix: string) {
  return fetchMock.mock.calls.find(
    ([input, init]) => init?.method === 'PUT' && String(input).endsWith(suffix),
  );
}

describe('saving', () => {
  it('stores counts from the backend response', async () => {
    const result = await startedSession();

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.save();
    });

    expect(result.current.counts).toEqual(COUNTS);
    expect(result.current.dirty).toBe(false);
  });

  it('saves an image with no boxes at all', async () => {
    // A reviewed image with nothing in it is a real negative example, not a skip.
    const result = await startedSession();

    act(() => result.current.setBoxes([]));
    await act(async () => {
      await result.current.save();
    });

    expect(putBody().boxes).toEqual([]);
  });

  it('clears an image\u2019s masks even when nothing on it has one', async () => {
    // The mask endpoint *replaces*, so an empty list is how "none any more" is said.
    // Skipping the call would leave rejected masks in the dataset for ever (doc 61).
    const result = await startedSession();

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.save();
    });

    expect(maskBody().masks).toEqual([]);
  });

  it('strips the client-side id before sending', async () => {
    const result = await startedSession();

    act(() => result.current.setBoxes([box({ id: 'client-only' })]));
    await act(async () => {
      await result.current.save();
    });

    const sent = putBody();
    expect(sent.boxes[0]).not.toHaveProperty('id');
    expect(sent.boxes[0]).toMatchObject({ label: 'positive', provenance: 'hand-drawn' });
  });

  it('sends the image dimensions the backend validates against', async () => {
    const result = await startedSession();

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.save();
    });

    expect(putBody()).toMatchObject({ path: '/pics/a.jpg', width: 200 });
  });

  it('keeps the work and reports the error when a save fails', async () => {
    const result = await startedSession({
      save: () => json({ error: { code: 'conflict', message: 'disk full' } }, 409),
    });

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.save();
    });

    expect(result.current.error).toBe('disk full');
    expect(result.current.dirty).toBe(true);
    expect(result.current.boxes).toHaveLength(1);
  });
});

describe('navigation', () => {
  it('saves unsaved work before moving on', async () => {
    const result = await startedSession();

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.next();
    });

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(true);
    expect(result.current.index).toBe(1);
  });

  it('stays put when the pre-navigation save fails', async () => {
    // Advancing past a failed save would silently discard the user's labels.
    const result = await startedSession({
      save: () => json({ error: { code: 'conflict', message: 'nope' } }, 409),
    });

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.next();
    });

    expect(result.current.index).toBe(0);
    expect(result.current.boxes).toHaveLength(1);
  });

  it('does not save when nothing changed', async () => {
    const result = await startedSession();

    await act(async () => {
      await result.current.next();
    });

    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false);
    expect(result.current.index).toBe(1);
  });

  it('clears boxes when moving to a new image', async () => {
    const result = await startedSession();

    act(() => result.current.setBoxes([box()]));
    await act(async () => {
      await result.current.next();
    });

    expect(result.current.boxes).toEqual([]);
    expect(result.current.dirty).toBe(false);
  });

  it('is bounded at both ends rather than wrapping', async () => {
    const result = await startedSession();

    expect(result.current.canGoPrevious).toBe(false);
    await act(async () => {
      await result.current.previous();
    });
    expect(result.current.index).toBe(0);

    for (let step = 0; step < 2; step += 1) {
      await act(async () => {
        await result.current.next();
      });
    }
    expect(result.current.index).toBe(2);
    expect(result.current.canGoNext).toBe(false);

    await act(async () => {
      await result.current.next();
    });
    expect(result.current.index).toBe(2);
  });
});
