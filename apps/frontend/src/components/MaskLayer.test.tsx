/**
 * The mask layer (doc 61).
 *
 * Three properties, and none of them is "a mask renders". It must never take a pointer or
 * an accessibility-tree entry — the box button drawn over each mask is the hit target, and
 * a second announcement would give a screen-reader user two entries for one annotation. It
 * must honour the same hiding rules as the boxes, or the threshold slider would leave
 * masks on screen for annotations the list says are filtered out. And it must composite
 * into **one** buffer: a canvas per mask is 15.8 MB apiece at full resolution, and thirty
 * translucent layers muddy every overlap.
 *
 * `decodeMap` is mocked because jsdom decodes no images. What is under test here is the
 * compositing — which pixels get which colour and which alpha — not the PNG decode, which
 * has its own reasons to be careful and its own file.
 */

import { render, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { numbered } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';
import type { RenderedImage } from '../lib/geometry';
import { MaskLayer, paintable } from './MaskLayer';

/** png string → the byte values `decodeMap` will report for it. */
const PIXELS: Record<string, number[]> = {};

vi.mock('../lib/decodeMap', () => ({
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

/** A 2x2 frame, so a whole mask is four numbers. */
const SIZE: readonly [number, number] = [2, 2];

function box(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return { id, label: 'positive', provenance: 'hand-drawn', x: 0, y: 0, w: 10, h: 10, ...over };
}

function segmented(id: string, png: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return box(id, {
    provenance: 'grounded-sam',
    mask: { rle: { size: SIZE, counts: [1, 2] }, png },
    ...over,
  });
}

let painted: Uint8ClampedArray | null = null;

function stubCanvas(): void {
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
        drawImage: () => undefined,
        imageSmoothingEnabled: true,
      }) as unknown as CanvasRenderingContext2D,
  );
}

/** The RGBA of one pixel of the composited buffer. */
function pixel(index: number): number[] {
  const data = painted;
  if (!data) throw new Error('nothing was painted');
  return [data[index * 4], data[index * 4 + 1], data[index * 4 + 2], data[index * 4 + 3]].map(
    (value) => value ?? 0,
  );
}

function renderLayer(
  boxes: CanvasBox[],
  hidden = new Set<string>(),
  selectedId: string | null = null,
) {
  return render(
    <MaskLayer
      boxes={numbered(boxes)}
      hidden={hidden}
      rendered={RENDERED}
      selectedId={selectedId}
    />,
  );
}

beforeEach(() => {
  for (const key of Object.keys(PIXELS)) delete PIXELS[key];
  stubCanvas();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('what it draws', () => {
  it('draws nothing at all when no annotation has a mask', () => {
    // Not an empty canvas: a layer over the image with nothing in it is still a layer.
    const { container } = renderLayer([box('a'), box('b')]);

    expect(container.querySelector('.masklayer')).toBeNull();
  });

  it('composites every mask into one canvas', () => {
    // One buffer, not one per annotation. Thirty full-resolution canvases is half a
    // gigabyte of pixel data and thirty translucent layers stacked on each other.
    PIXELS['A'] = [255, 0, 0, 0];
    PIXELS['B'] = [0, 255, 0, 0];
    const { container } = renderLayer([segmented('a', 'A'), segmented('b', 'B')]);

    expect(container.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('sizes the canvas from the RLE, which is height-first', () => {
    // COCO's `size` is [height, width] — the reverse of every other size in the app.
    // Getting it backwards renders every mask transposed and silently wrong.
    const wide = segmented('a', 'A');
    const { container } = render(
      <MaskLayer
        boxes={numbered([
          { ...wide, mask: { rle: { size: [600, 800], counts: [1, 2] }, png: 'A' } },
        ])}
        hidden={new Set()}
        rendered={RENDERED}
        selectedId={null}
      />,
    );
    const canvas = container.querySelector('canvas') as HTMLCanvasElement;

    expect(canvas.width).toBe(800);
    expect(canvas.height).toBe(600);
  });

  it('places itself over the rendered image, not the container', () => {
    // An object-fit:contain image is letterboxed; using the container would offset every
    // mask by the letterbox.
    PIXELS['A'] = [255, 0, 0, 0];
    const { container } = renderLayer([segmented('a', 'A')]);
    const canvas = container.querySelector('canvas') as HTMLElement;

    expect(canvas.style.left).toBe('10px');
    expect(canvas.style.top).toBe('20px');
    expect(canvas.style.width).toBe('400px');
  });
});

describe('compositing', () => {
  it('paints foreground pixels in the verdict colour and leaves the rest clear', async () => {
    PIXELS['A'] = [255, 0, 0, 0];
    renderLayer([segmented('a', 'A')]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0)).toEqual([74, 222, 128, 115]);
    // Background stays fully transparent — an opaque background is a rectangle over the
    // picture, which is the bug this whole layer exists to avoid.
    expect(pixel(1)).toEqual([0, 0, 0, 0]);
  });

  it('uses the verdict colour, so a rejected mask reads as rejected', async () => {
    PIXELS['A'] = [255, 0, 0, 0];
    renderLayer([segmented('a', 'A', { label: 'negative' })]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0).slice(0, 3)).toEqual([248, 113, 113]);
  });

  it('treats a dithered background byte as background, not as the object', async () => {
    // The reported "fizzle". A browser that colour-manages the PNG on the way in turns a
    // scatter of 0s into 1s; `value > 0` promotes every one of them to a painted pixel and
    // speckles the whole frame. `decodeMap` stops the conversion; this makes it not matter.
    PIXELS['A'] = [255, 1, 2, 0];
    renderLayer([segmented('a', 'A')]);

    await waitFor(() => expect(painted).not.toBeNull());
    expect(pixel(0)[3]).toBe(115);
    expect(pixel(1)[3]).toBe(0);
    expect(pixel(2)[3]).toBe(0);
  });

  it('lets the later mask win where two overlap', async () => {
    // Last-writer-wins, the same rule the backend's own composited index map follows —
    // rather than two translucent layers multiplying into a third colour.
    PIXELS['A'] = [255, 255, 0, 0];
    PIXELS['B'] = [0, 255, 0, 0];
    renderLayer([segmented('a', 'A'), segmented('b', 'B', { label: 'unclear' })]);

    await waitFor(() => expect(painted).not.toBeNull());
    await waitFor(() => expect(pixel(1).slice(0, 3)).toEqual([251, 191, 36]));
    // The pixel only the first mask covers keeps the first mask's colour.
    expect(pixel(0).slice(0, 3)).toEqual([74, 222, 128]);
  });

  it('brightens the selected mask rather than outlining it', async () => {
    // An outline would compete with the box button's own focus ring, drawn on top.
    PIXELS['A'] = [255, 0, 0, 0];
    PIXELS['B'] = [0, 0, 0, 255];
    renderLayer([segmented('a', 'A'), segmented('b', 'B')], new Set(), 'a');

    await waitFor(() => expect(painted).not.toBeNull());
    await waitFor(() => expect(pixel(3)[3]).toBe(115));
    expect(pixel(0)[3]).toBeGreaterThan(pixel(3)[3] as number);
  });
});

describe('what it refuses to do', () => {
  it('adds nothing to the accessibility tree', () => {
    // Each annotation is announced once, by its button.
    PIXELS['A'] = [255, 0, 0, 0];
    const { container } = renderLayer([segmented('a', 'A')]);

    expect(container.querySelector('.masklayer')).toHaveAttribute('aria-hidden', 'true');
    expect(container.querySelectorAll('[role="img"]')).toHaveLength(0);
  });
});

describe('which annotations it paints', () => {
  it('skips a box with no mask', () => {
    expect(
      paintable(numbered([box('a'), segmented('b', 'B')]), new Set()).map((e) => e.id),
    ).toEqual(['b']);
  });

  it('skips whatever is hidden', () => {
    // Otherwise lowering the cutoff — or hiding the boxes to draw on a clear image —
    // would leave masks on screen for annotations the list says are gone.
    expect(
      paintable(numbered([segmented('a', 'A'), segmented('b', 'B')]), new Set(['a'])).map(
        (e) => e.id,
      ),
    ).toEqual(['b']);
  });

  it('draws nothing when every mask is hidden', () => {
    const { container } = renderLayer([segmented('a', 'A')], new Set(['a']));

    expect(container.querySelector('.masklayer')).toBeNull();
  });
});
