/**
 * Loading an image's stored masks back into the Studio (doc 61).
 *
 * This is the rule that makes storing masks safe rather than destructive. A save
 * *replaces* an image's whole mask set, so a session that opened an already-segmented
 * image without its masks would wipe every one of them on the first save — silently, and
 * with a success message.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CONFIG, COUNTS, IMAGES, box, json } from './session.testkit';
import { useAnnotationSession } from './useAnnotationSession';

const fetchMock = vi.fn<typeof fetch>();

const STORED_MASK = {
  label: 'positive',
  provenance: 'grounded-sam',
  rle: { size: [100, 200], counts: [5, 2, 2, 2, 5] },
  x: 10,
  y: 20,
  w: 30,
  h: 40,
  score: 0.82,
  prompt: 'sky',
  producer: { id: 'grounded-sam', label: 'Grounded SAM', concept: 'sky' },
  mask_png: 'iVBOR',
};

/** Paths whose mask read has been asked for, in order. */
const maskReads: string[] = [];

function route(masksFor: (path: string) => unknown[] = () => [STORED_MASK]): void {
  fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/images/masks') && init?.method !== 'PUT') {
      const path = decodeURIComponent(url.split('path=')[1] ?? '');
      maskReads.push(path);
      return Promise.resolve(json({ path, masks: masksFor(path) }));
    }
    if (url.includes('/annotate/folder')) {
      return Promise.resolve(json({ folder: '/pics', images: IMAGES }));
    }
    if (init?.method === 'PUT') return Promise.resolve(json(COUNTS));
    return Promise.resolve(json({}));
  });
}

async function startedSession() {
  const { result } = renderHook(() => useAnnotationSession(CONFIG));
  await waitFor(() => expect(result.current.images).toHaveLength(3));
  act(() => result.current.reportImageSize(200, 100));
  return result;
}

beforeEach(() => {
  maskReads.length = 0;
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('loading stored masks', () => {
  it('merges them into the one list of annotations', async () => {
    // Not a second array: the numbering, the threshold, the verdict buttons and the class
    // picker all work on `boxes`, and none of them should learn that some annotations came
    // from a different table.
    route();
    const result = await startedSession();

    await waitFor(() => expect(result.current.boxes).toHaveLength(1));
    expect(result.current.boxes[0]?.mask?.png).toBe('iVBOR');
  });

  it('gives a mask the derived box as its geometry', async () => {
    // The hit target. Mask pixels cannot be focused; this rect is what becomes a button.
    route();
    const result = await startedSession();

    await waitFor(() => expect(result.current.boxes).toHaveLength(1));
    const loaded = result.current.boxes[0];
    expect([loaded?.x, loaded?.y, loaded?.w, loaded?.h]).toEqual([10, 20, 30, 40]);
  });

  it('carries the class and the producer snapshot', async () => {
    route();
    const result = await startedSession();

    await waitFor(() => expect(result.current.boxes).toHaveLength(1));
    expect(result.current.boxes[0]?.text).toBe('sky');
    expect(result.current.boxes[0]?.producer?.id).toBe('grounded-sam');
  });

  it('does not mark the session dirty', async () => {
    // Loading is not editing. A dirty session saves on navigate, so this would write every
    // image back the moment it was looked at.
    route();
    const result = await startedSession();

    await waitFor(() => expect(result.current.boxes).toHaveLength(1));
    expect(result.current.dirty).toBe(false);
  });

  it('reads the next image on navigation', async () => {
    route();
    const result = await startedSession();
    await waitFor(() => expect(result.current.boxes).toHaveLength(1));

    await act(async () => {
      await result.current.next();
    });

    await waitFor(() => expect(maskReads).toContain('/pics/b.jpg'));
  });

  it('does not merge the same masks twice', async () => {
    route();
    const result = await startedSession();
    await waitFor(() => expect(result.current.boxes).toHaveLength(1));

    // A re-render must not re-append. `useStoredMasks` records which image it has done.
    act(() => result.current.reportImageSize(200, 100));
    await new Promise((resolve) => setTimeout(resolve, 10));

    expect(result.current.boxes).toHaveLength(1);
  });
});

describe('when it must not land', () => {
  it('leaves an edited canvas alone', async () => {
    // A load arriving after the reviewer has started work would put annotations under
    // their hands.
    route(() => [STORED_MASK]);
    const result = await startedSession();
    act(() => result.current.setBoxes([box({ id: 'drawn' })]));

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(result.current.boxes.map((entry) => entry.id)).toEqual(['drawn']);
  });

  it('survives the read failing', async () => {
    // Non-fatal by design: the boxes are already on screen and a failed mask read must not
    // take the review surface down with it.
    fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
      const url = String(input);
      if (url.includes('/images/masks') && init?.method !== 'PUT') {
        return Promise.resolve(json({ error: { code: 'oops', message: 'no' } }, 500));
      }
      if (url.includes('/annotate/folder')) {
        return Promise.resolve(json({ folder: '/pics', images: IMAGES }));
      }
      return Promise.resolve(json({}));
    });
    const result = await startedSession();

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(result.current.error).toBeNull();
    expect(result.current.boxes).toEqual([]);
  });
});

describe('the round trip', () => {
  it('writes loaded masks back rather than dropping them', async () => {
    // The whole point. Without the load, this save would clear the image's masks.
    route();
    const result = await startedSession();
    await waitFor(() => expect(result.current.boxes).toHaveLength(1));

    act(() => result.current.setBoxes([...result.current.boxes]));
    await act(async () => {
      await result.current.save();
    });

    const put = fetchMock.mock.calls.find(
      ([input, init]) => init?.method === 'PUT' && String(input).endsWith('/images/masks'),
    );
    const body = JSON.parse(String(put?.[1]?.body)) as { masks: unknown[] };
    expect(body.masks).toHaveLength(1);
  });
});
