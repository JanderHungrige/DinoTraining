/**
 * Which table an annotation goes to (doc 61).
 *
 * The load-bearing rule is **one annotation per object**. `build_coco` walks the boxes and
 * masks tables independently and emits each as its own annotation, and a stored mask
 * already exports with `segmentation`, a `bbox` derived from the RLE, and `area`. Writing
 * a box row as well would put two annotations on one object in every export and silently
 * double every segmented object in anything trained from it — a failure with no error
 * message anywhere, which is why it is pinned here rather than left to review.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { partitionByMask, saveAnnotations } from './saveAnnotations';
import type { CanvasBox } from '../types/annotation';

const fetchMock = vi.fn<typeof fetch>();

const COUNTS = { images: 1, boxes: 1, masks: 1, positive: 2, negative: 0, unclear: 0 };

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function box(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return { id, label: 'positive', provenance: 'hand-drawn', x: 1, y: 2, w: 3, h: 4, ...over };
}

function segmented(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return box(id, {
    provenance: 'grounded-sam',
    mask: { rle: { size: [4, 4], counts: [5, 2, 2, 2, 5] }, png: 'iVBOR' },
    ...over,
  });
}

const IMAGE = { path: '/pics/a.png', width: 4, height: 4, prompt: null };

/** Bodies sent, keyed by which endpoint took them. */
function sent(suffix: string): Record<string, unknown> {
  const call = fetchMock.mock.calls.find(
    ([input, init]) => init?.method === 'PUT' && String(input).endsWith(suffix),
  );
  return JSON.parse(String(call?.[1]?.body ?? '{}')) as Record<string, unknown>;
}

function urlsInOrder(): string[] {
  return fetchMock.mock.calls
    .filter(([, init]) => init?.method === 'PUT')
    .map(([input]) => String(input).replace(/^.*\/api\/v1/, ''));
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(() => Promise.resolve(json(COUNTS)));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('partitionByMask', () => {
  it('splits on whether the annotation carries a segmentation', () => {
    const { segmented: withMask, plain } = partitionByMask([
      box('a'),
      segmented('b'),
      box('c'),
    ]);

    expect(withMask.map((entry) => entry.id)).toEqual(['b']);
    expect(plain.map((entry) => entry.id)).toEqual(['a', 'c']);
  });
});

describe('saving', () => {
  it('sends a segmented annotation to the masks table only', async () => {
    await saveAnnotations('d1', IMAGE, [segmented('a', { text: 'sky' })]);

    expect(sent('/images/masks')['masks']).toHaveLength(1);
    // The whole point: no box row for the same object.
    expect(sent('/images')['boxes']).toEqual([]);
  });

  it('sends a plain box to the boxes table only', async () => {
    await saveAnnotations('d1', IMAGE, [box('a', { text: 'signal' })]);

    expect(sent('/images')['boxes']).toHaveLength(1);
    expect(sent('/images/masks')['masks']).toEqual([]);
  });

  it('splits a mixed image between the two', async () => {
    // The ordinary case after a SAM run plus a hand-drawn correction.
    await saveAnnotations('d1', IMAGE, [segmented('a'), box('b'), segmented('c')]);

    expect(sent('/images/masks')['masks']).toHaveLength(2);
    expect(sent('/images')['boxes']).toHaveLength(1);
  });

  it('sends both sets even when one is empty', async () => {
    // Each endpoint *replaces*, so an empty list is how "none any more" is said. Skipping
    // the call would leave an image's rejected masks in the dataset for ever.
    await saveAnnotations('d1', IMAGE, []);

    expect(urlsInOrder()).toEqual(['/datasets/d1/images/masks', '/datasets/d1/images']);
  });

  it('writes masks before boxes', async () => {
    // Not atomic — there is no endpoint that takes both. A failed mask write leaves the
    // previous masks *and* the previous boxes, which is simply "the save did not happen";
    // the other order guarantees the mismatched state instead of making it the rare one.
    await saveAnnotations('d1', IMAGE, [segmented('a'), box('b')]);

    expect(urlsInOrder()).toEqual(['/datasets/d1/images/masks', '/datasets/d1/images']);
  });

  it('renames the class to prompt on the mask path too', async () => {
    // `text` is the canvas's name and the store calls it `prompt`. Sending `text` has
    // pydantic drop it and land `prompt` NULL — the doc 31 bug, on a second path.
    await saveAnnotations('d1', IMAGE, [segmented('a', { text: 'sky' })]);

    const masks = sent('/images/masks')['masks'] as Record<string, unknown>[];
    expect(masks[0]?.['prompt']).toBe('sky');
    expect(masks[0]).not.toHaveProperty('text');
  });

  it('sends the RLE, not the preview', async () => {
    // The PNG is what gets drawn; the RLE is what gets stored. Sending the preview would
    // store a picture of a mask instead of a mask.
    await saveAnnotations('d1', IMAGE, [segmented('a')]);

    const masks = sent('/images/masks')['masks'] as Record<string, unknown>[];
    expect(masks[0]?.['rle']).toEqual({ size: [4, 4], counts: [5, 2, 2, 2, 5] });
    expect(masks[0]).not.toHaveProperty('png');
  });

  it('carries the verdict the reviewer set', async () => {
    await saveAnnotations('d1', IMAGE, [segmented('a', { label: 'negative' })]);

    const masks = sent('/images/masks')['masks'] as Record<string, unknown>[];
    expect(masks[0]?.['label']).toBe('negative');
  });

  it('returns the backend counters from the second write', async () => {
    // Never a local tally — that drifts the first time a save fails.
    const counts = await saveAnnotations('d1', IMAGE, [segmented('a')]);

    expect(counts).toEqual(COUNTS);
  });

  it('does not write boxes when the mask write failed', async () => {
    fetchMock.mockImplementation((input: unknown) =>
      String(input).endsWith('/images/masks')
        ? Promise.resolve(
            new Response(JSON.stringify({ error: { code: 'unprocessable', message: 'bad' } }), {
              status: 422,
              headers: { 'Content-Type': 'application/json' },
            }),
          )
        : Promise.resolve(json(COUNTS)),
    );

    await expect(saveAnnotations('d1', IMAGE, [segmented('a'), box('b')])).rejects.toThrow();
    expect(urlsInOrder()).toEqual(['/datasets/d1/images/masks']);
  });
});
