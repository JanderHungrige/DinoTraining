/**
 * The shared mask compositor.
 *
 * **Both** mask surfaces render through this — the Annotation Studio's `MaskLayer` and the
 * Dataset Generator's `MaskReviewCanvas` — which is the whole reason it exists. Each had
 * grown its own copy, and the green fizzle was reported twice: once per copy, months apart,
 * for the identical reason. These tests are the thing that stops a third.
 *
 * `decodeMap` is mocked because jsdom decodes no images. What is under test is the
 * compositing — which pixels get which colour and which alpha — not the PNG decode, which
 * has its own file and its own reasons to be careful.
 */

import { render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { RenderedImage } from '../../lib/geometry';
import { CompositedMasks, type PaintedMask } from './CompositedMasks';

/** png string → the byte values `decodeMap` will report for it. */
const PIXELS: Record<string, number[]> = {};

vi.mock('../../lib/decodeMap', () => ({
  decodeMap: vi.fn(async (encoded: string, width: number, height: number) => ({
    values: new Uint8ClampedArray(PIXELS[encoded] ?? new Array(width * height).fill(0)),
    width,
    height,
  })),
}));

const RENDERED: RenderedImage = {
  width: 400,
  height: 300,
  offsetX: 10,
  offsetY: 20,
  naturalWidth: 800,
  naturalHeight: 600,
};

let painted: Uint8ClampedArray | null = null;

beforeEach(() => {
  for (const key of Object.keys(PIXELS)) delete PIXELS[key];
  painted = null;
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
    () =>
      ({
        createImageData: (w: number, h: number) => ({
          data: new Uint8ClampedArray(w * h * 4),
          width: w,
          height: h,
        }),
        putImageData: (image: { data: Uint8ClampedArray }) => {
          painted = image.data;
        },
      }) as unknown as CanvasRenderingContext2D,
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** RGBA of one pixel of the composited buffer. */
function pixel(index: number): number[] {
  const data = painted;
  if (!data) throw new Error('nothing was painted');
  return [data[index * 4], data[index * 4 + 1], data[index * 4 + 2], data[index * 4 + 3]].map(
    (value) => value ?? 0,
  );
}

/** A 2x2 frame, so a whole mask is four numbers. */
function renderMasks(masks: PaintedMask[], selectedId: string | null = null) {
  return render(
    <CompositedMasks
      masks={masks}
      width={2}
      height={2}
      rendered={RENDERED}
      selectedId={selectedId}
    />,
  );
}

function mask(id: string, png: string, label: PaintedMask['label'] = 'positive'): PaintedMask {
  return { id, label, png };
}

describe('the foreground test', () => {
  it('treats a dithered background byte as background, not as the object', async () => {
    // **The bug, twice reported.** WebKit colour-manages the PNG on the way in whatever
    // `colorSpaceConversion: 'none'` asks, so a background of 0 arrives as a scatter of
    // 0s and small values. `> 0` promotes every one of them to a painted pixel and
    // speckles the whole frame in green.
    PIXELS['A'] = [255, 1, 2, 127];
    renderMasks([mask('a', 'A')]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0)[3]).toBe(115);
    expect(pixel(1)[3]).toBe(0);
    expect(pixel(2)[3]).toBe(0);
    // 127 is still below the midpoint. Anything at or above 128 is the object.
    expect(pixel(3)[3]).toBe(0);
  });

  it('treats a dithered object byte as the object', async () => {
    PIXELS['A'] = [255, 254, 128, 0];
    renderMasks([mask('a', 'A')]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0)[3]).toBe(115);
    expect(pixel(1)[3]).toBe(115);
    expect(pixel(2)[3]).toBe(115);
    expect(pixel(3)[3]).toBe(0);
  });
});

describe('compositing', () => {
  it('paints every mask into one canvas', async () => {
    // Not one canvas each: a full-resolution buffer is 15.8 MB at 2464x1600, so twenty
    // masks is ~300 MB and twenty translucent layers darkening each overlap.
    PIXELS['A'] = [255, 0, 0, 0];
    PIXELS['B'] = [0, 255, 0, 0];
    const { container } = renderMasks([mask('a', 'A'), mask('b', 'B')]);

    expect(container.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('tints by verdict, so a rejected mask reads as rejected', async () => {
    PIXELS['A'] = [255, 0, 0, 0];
    renderMasks([mask('a', 'A', 'negative')]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0).slice(0, 3)).toEqual([248, 113, 113]);
  });

  it('lets the later mask win where two overlap', async () => {
    // Last-writer-wins, the same rule the backend's composited index map follows, rather
    // than two translucent layers multiplying into a third colour nobody chose.
    PIXELS['A'] = [255, 255, 0, 0];
    PIXELS['B'] = [0, 255, 0, 0];
    renderMasks([mask('a', 'A'), mask('b', 'B', 'unclear')]);

    await waitFor(() => expect(painted).not.toBeNull());
    await waitFor(() => expect(pixel(1).slice(0, 3)).toEqual([251, 191, 36]));
    expect(pixel(0).slice(0, 3)).toEqual([74, 222, 128]);
  });

  it('brightens the selected mask rather than outlining it', async () => {
    // An outline would compete with the caller's own focus ring, drawn on top of it.
    PIXELS['A'] = [255, 0, 0, 0];
    PIXELS['B'] = [0, 0, 0, 255];
    renderMasks([mask('a', 'A'), mask('b', 'B')], 'a');

    await waitFor(() => expect(painted).not.toBeNull());
    await waitFor(() => expect(pixel(3)[3]).toBe(115));
    expect(pixel(0)[3]).toBeGreaterThan(pixel(3)[3] as number);
  });
});

describe('what it refuses to do', () => {
  it('renders nothing at all when there are no masks', () => {
    const { container } = renderMasks([]);

    expect(container.querySelector('canvas')).toBeNull();
  });

  it('adds nothing to the accessibility tree', () => {
    // Every caller draws a labelled button over each mask. Announcing the mask here too
    // would give a screen-reader user two entries for one thing.
    PIXELS['A'] = [255, 0, 0, 0];
    const { container } = renderMasks([mask('a', 'A')]);

    expect(container.querySelector('canvas')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelectorAll('[role="img"]')).toHaveLength(0);
  });

  it('places itself over the rendered image, not the container', () => {
    // An object-fit:contain image is letterboxed; using the container would offset every
    // mask by the letterbox.
    PIXELS['A'] = [255, 0, 0, 0];
    const { container } = renderMasks([mask('a', 'A')]);
    const canvas = container.querySelector('canvas') as HTMLElement;

    expect(canvas.style.left).toBe('10px');
    expect(canvas.style.top).toBe('20px');
    expect(canvas.style.width).toBe('400px');
  });
});
