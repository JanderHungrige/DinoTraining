/**
 * The registry is the point of this feature, so it is tested as a registry.
 *
 * The load-bearing property is not "a mask renders" but "dispatch happens on
 * `render_hint` and every hint has an entry" — that is what lets a head type be added to
 * the backend later and render here without this wave's code being touched.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { decodeMap } from '../../lib/decodeMap';

import type { Prediction, RenderHint } from '../../api/inference';
import type { RenderedImage } from '../../lib/geometry';
import { OVERLAY_RENDERERS, renderOverlayFor } from './registry';

vi.mock('../../lib/decodeMap', () => ({ decodeMap: vi.fn() }));

// A benign default: most tests here assert on the canvas element, not on pixels, and an
// unmocked `decodeMap` would return undefined and throw inside the effect.
beforeEach(() => {
  vi.mocked(decodeMap).mockResolvedValue(null);
});
import { topLabels } from './LabelOverlay';

const RENDERED: RenderedImage = {
  width: 400,
  height: 300,
  offsetX: 10,
  offsetY: 20,
  naturalWidth: 800,
  naturalHeight: 600,
};

/** A 2x2 greyscale PNG. Enough for the canvas path; jsdom will not decode it. */
const TINY_PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAAAAACIvoBnAAAAEUlEQVR4nGP4z8DAwMDAxAAEAA8AAv0DkD8AAAAASUVORK5CYII=';

function prediction(hint: RenderHint, payload: Record<string, unknown>): Prediction {
  return {
    instance_id: 'inst-1',
    head_name: 'A head with provenance',
    head_type_id: 'linear-thing',
    task: 'whatever',
    render_hint: hint,
    class_names: ['cat', 'dog', 'bird'],
    payload,
    grid: [32, 32],
    elapsed_ms: 12,
  };
}

describe('OVERLAY_RENDERERS', () => {
  it('has exactly one entry per render hint', () => {
    // The backend's RenderHint union, mirrored. A hint added there and not here is the
    // failure this asserts against.
    const hints: RenderHint[] = ['labels', 'boxes', 'masks', 'depth-map'];

    expect(Object.keys(OVERLAY_RENDERERS).sort()).toEqual([...hints].sort());
  });

  it('dispatches on render_hint, not on the task string', () => {
    // Same task, two hints: if anything keyed off `task` this would render the same
    // thing twice.
    const asLabels = prediction('labels', { scores: [0.7, 0.2, 0.1] });
    const asBoxes = {
      ...prediction('boxes', { boxes: [[0, 0, 10, 10]], scores: [0.9], classes: [1] }),
      task: asLabels.task,
    };

    const { container: labelDom } = render(<>{renderOverlayFor(asLabels, RENDERED)}</>);
    const { container: boxDom } = render(<>{renderOverlayFor(asBoxes, RENDERED)}</>);

    expect(labelDom.querySelector('.overlay__labels')).not.toBeNull();
    expect(boxDom.querySelector('.overlay__boxes')).not.toBeNull();
  });

  it('renders nothing rather than crashing on a payload missing its data', () => {
    // A head that returned an empty result must not take the pane down with it.
    for (const hint of ['labels', 'boxes', 'masks', 'depth-map'] as RenderHint[]) {
      expect(() => renderOverlayFor(prediction(hint, {}), RENDERED)).not.toThrow();
    }
  });
});

describe('boxes', () => {
  it('places a box using the rendered geometry, not the container', () => {
    // Source is 800x600 shown at 400x300 with a (10, 20) letterbox offset, so a box at
    // (100, 60) size 200x120 lands at (60, 50) size 100x60. Getting this wrong offsets
    // every box by the letterbox — the failure lib/geometry.ts exists to prevent.
    const item = prediction('boxes', {
      boxes: [[100, 60, 200, 120]],
      scores: [0.83],
      classes: [1],
    });

    const { container } = render(<>{renderOverlayFor(item, RENDERED)}</>);
    const box = container.querySelector('.overlay__box') as HTMLElement;

    expect(box.style.left).toBe('60px');
    expect(box.style.top).toBe('50px');
    expect(box.style.width).toBe('100px');
    expect(box.style.height).toBe('60px');
  });

  it('names the class from the training order and shows the score', () => {
    const item = prediction('boxes', {
      boxes: [[0, 0, 10, 10]],
      scores: [0.83],
      classes: [2],
    });

    render(<>{renderOverlayFor(item, RENDERED)}</>);

    expect(screen.getByText(/bird/)).toBeInTheDocument();
    expect(screen.getByText(/0\.83/)).toBeInTheDocument();
  });

  it('falls back to a placeholder name for a class it cannot name', () => {
    // A pretrained default carries 1000 ImageNet ids with no names attached.
    const item = prediction('boxes', {
      boxes: [[0, 0, 10, 10]],
      scores: [0.5],
      classes: [900],
    });

    render(<>{renderOverlayFor(item, RENDERED)}</>);

    expect(screen.getByText(/class 900/)).toBeInTheDocument();
  });

  it('reads boxes, scores and classes positionally', () => {
    const item = prediction('boxes', {
      boxes: [
        [0, 0, 10, 10],
        [20, 20, 10, 10],
      ],
      scores: [0.9, 0.4],
      classes: [0, 2],
    });

    const { container } = render(<>{renderOverlayFor(item, RENDERED)}</>);
    const tags = [...container.querySelectorAll('.overlay__boxtag')].map((t) => t.textContent);

    expect(tags[0]).toContain('cat');
    expect(tags[0]).toContain('0.90');
    expect(tags[1]).toContain('bird');
    expect(tags[1]).toContain('0.40');
  });
});

describe('labels', () => {
  it('ranks by score rather than by class order', () => {
    const item = prediction('labels', { scores: [0.1, 0.2, 0.7] });

    expect(topLabels(item).map((entry) => entry.name)).toEqual(['bird', 'dog', 'cat']);
  });

  it('shows the score, not only the winner', () => {
    // "cat 0.92" and "cat 0.41" are different claims; the winner alone hides that.
    render(<>{renderOverlayFor(prediction('labels', { scores: [0.92, 0.05, 0.03] }), RENDERED)}</>);

    expect(screen.getByText('0.920')).toBeInTheDocument();
  });

  it('caps the list so a 1000-class head does not fill the pane', () => {
    const scores = Array.from({ length: 1000 }, (_, i) => i / 1000);

    expect(topLabels(prediction('labels', { scores }))).toHaveLength(5);
  });
});

describe('dense maps', () => {
  it('sizes the canvas to the map and positions it on the rendered image', () => {
    const item = prediction('masks', {
      mask_png: TINY_PNG,
      present_classes: [0, 1],
      width: 800,
      height: 600,
    });

    const { container } = render(<>{renderOverlayFor(item, RENDERED)}</>);
    const canvas = container.querySelector('canvas') as HTMLCanvasElement;

    // Backing store is the map's own resolution; CSS box is where the image is drawn.
    expect(canvas.width).toBe(800);
    expect(canvas.height).toBe(600);
    expect(canvas.style.left).toBe('10px');
    expect(canvas.style.top).toBe('20px');
    expect(canvas.style.width).toBe('400px');
    expect(canvas.style.height).toBe('300px');
  });

  it('draws depth more opaquely than a mask', () => {
    // A mask is read against the pixels underneath it; a depth map replaces them.
    const mask = prediction('masks', {
      mask_png: TINY_PNG,
      present_classes: [0],
      width: 8,
      height: 8,
    });
    const depth = prediction('depth-map', {
      depth_png: TINY_PNG,
      min: 1,
      max: 5,
      width: 8,
      height: 8,
    });

    const { container: maskDom } = render(<>{renderOverlayFor(mask, RENDERED)}</>);
    const { container: depthDom } = render(<>{renderOverlayFor(depth, RENDERED)}</>);

    const maskOpacity = Number((maskDom.querySelector('canvas') as HTMLElement).style.opacity);
    const depthOpacity = Number((depthDom.querySelector('canvas') as HTMLElement).style.opacity);
    expect(depthOpacity).toBeGreaterThan(maskOpacity);
  });

  it('labels the map with the head that produced it', () => {
    const item = prediction('masks', {
      mask_png: TINY_PNG,
      present_classes: [0],
      width: 8,
      height: 8,
    });

    render(<>{renderOverlayFor(item, RENDERED)}</>);

    // Provenance, never a filename — doc 12's contract reaching the overlay.
    expect(screen.getByLabelText(/A head with provenance/)).toBeInTheDocument();
  });
});

/**
 * Whether class 0 is painted — the difference between "no answer" and a broken-looking one.
 *
 * Masks were rendered with no `alphaFor`, so every pixel came out opaque. For an ADE20k
 * segmenter that is right — its class 0 is `wall`. For a concept segmenter class 0 is
 * background, and an all-background result was not an empty overlay but the whole frame
 * washed in one flat colour at 55% opacity. Asking Grounded SAM for "sky" and getting a
 * uniform red rectangle is what "very bad results" looked like.
 *
 * `decodeMap` is mocked: jsdom decodes no images, and what is under test here is the
 * *decision* about class 0, not the decode.
 */
describe('mask background', () => {
  /** Pixel class indices in, the RGBA buffer the overlay paints out. */
  async function paint(
    classNames: readonly string[],
    values: readonly number[],
  ): Promise<Uint8ClampedArray> {
    vi.mocked(decodeMap).mockResolvedValue({
      values: new Uint8ClampedArray(values),
      width: values.length,
      height: 1,
    });

    let written: Uint8ClampedArray | null = null;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
      () =>
        ({
          createImageData: (w: number, h: number) => ({
            data: new Uint8ClampedArray(w * h * 4),
            width: w,
            height: h,
          }),
          putImageData: (image: { data: Uint8ClampedArray }) => {
            written = image.data;
          },
        }) as unknown as CanvasRenderingContext2D,
    );

    render(
      <>
        {renderOverlayFor(
          {
            ...prediction('masks', {
              mask_png: TINY_PNG,
              present_classes: [...new Set(values)],
              width: values.length,
              height: 1,
            }),
            class_names: classNames,
          },
          RENDERED,
        )}
      </>,
    );

    await waitFor(() => expect(written).not.toBeNull());
    return written as unknown as Uint8ClampedArray;
  }

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('leaves a named background transparent', async () => {
    const painted = await paint(['background', 'sky'], [0, 1, 0]);

    expect(painted[3]).toBe(0);
    expect(painted[7]).toBe(255);
    expect(painted[11]).toBe(0);
  });

  it('paints class 0 when it is a real class, as ADE20k\u2019s wall is', async () => {
    const painted = await paint(['wall', 'sky'], [0, 1]);

    expect(painted[3]).toBe(255);
    expect(painted[7]).toBe(255);
  });
});

/**
 * The stride (`class_stride`) — what finally killed the fizzle in the packaged app.
 *
 * Adjacent class indices make terrible pixel values. With a single phrase a concept
 * segmenter's classes are 0 and 1, and WebKit colour-manages the PNG on the way in
 * whatever `colorSpaceConversion: 'none'` asks, dithering the low bits: half the
 * background arrives as class 1 and is painted. Spread to 0 and 255 it takes a 128-level
 * error to confuse them, and rounding here absorbs whatever the conversion did.
 */
describe('the class stride', () => {
  async function paintStrided(
    values: readonly number[],
    stride: number | undefined,
  ): Promise<Uint8ClampedArray> {
    vi.mocked(decodeMap).mockResolvedValue({
      values: new Uint8ClampedArray(values),
      width: values.length,
      height: 1,
    });

    let written: Uint8ClampedArray | null = null;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
      () =>
        ({
          createImageData: (w: number, h: number) => ({
            data: new Uint8ClampedArray(w * h * 4),
            width: w,
            height: h,
          }),
          putImageData: (image: { data: Uint8ClampedArray }) => {
            written = image.data;
          },
        }) as unknown as CanvasRenderingContext2D,
    );

    render(
      <>
        {renderOverlayFor(
          {
            ...prediction('masks', {
              mask_png: TINY_PNG,
              width: values.length,
              height: 1,
              ...(stride === undefined ? {} : { class_stride: stride }),
            }),
            class_names: ['background', 'sky'],
          },
          RENDERED,
        )}
      </>,
    );

    await waitFor(() => expect(written).not.toBeNull());
    return written as unknown as Uint8ClampedArray;
  }

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('reads a strided value back as its class', async () => {
    // 255 with a stride of 255 is class 1, not class 255.
    const painted = await paintStrided([0, 255], 255);

    expect(painted[3]).toBe(0);
    expect(painted[7]).toBe(255);
  });

  it('rounds a dithered background back down to background', async () => {
    // The bug, reproduced at the level it survives at: WebKit turns some 0s into small
    // values, and without the stride those *are* class 1.
    const painted = await paintStrided([0, 1, 2, 255], 255);

    expect(painted[3]).toBe(0);
    expect(painted[7]).toBe(0);
    expect(painted[11]).toBe(0);
    expect(painted[15]).toBe(255);
  });

  it('rounds a dithered object back up to its class', async () => {
    const painted = await paintStrided([253, 254], 255);

    expect(painted[3]).toBe(255);
    expect(painted[7]).toBe(255);
  });

  it('falls back to a stride of 1 when the backend does not send one', async () => {
    // An older backend, or the depth path. The pre-stride encoding still renders.
    const painted = await paintStrided([0, 1], undefined);

    expect(painted[3]).toBe(0);
    expect(painted[7]).toBe(255);
  });

  it('gives one colour per class, not one per pixel value', async () => {
    // Three phrases at stride 85: values 85, 170, 255 must be classes 1, 2, 3.
    const painted = await paintStrided([85, 170, 255], 85);
    const colours = [0, 1, 2].map((i) => painted.slice(i * 4, i * 4 + 3).join(','));

    expect(new Set(colours).size).toBe(3);
  });
});
