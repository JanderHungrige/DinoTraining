/**
 * The registry is the point of this feature, so it is tested as a registry.
 *
 * The load-bearing property is not "a mask renders" but "dispatch happens on
 * `render_hint` and every hint has an entry" — that is what lets a head type be added to
 * the backend later and render here without this wave's code being touched.
 */

import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Prediction, RenderHint } from '../../api/inference';
import type { RenderedImage } from '../../lib/geometry';
import { OVERLAY_RENDERERS, renderOverlayFor } from './registry';
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
 * A regression file's worth of context: masks were rendered with no `alphaFor`, so every
 * pixel came out opaque. For an ADE20k segmenter that is right — its class 0 is `wall`.
 * For a concept segmenter class 0 is background, and an all-background result was not an
 * empty overlay but the whole frame washed in one flat colour at 55% opacity. Asking
 * Grounded SAM for "sky" and getting a uniform red rectangle is what "very bad results"
 * looked like.
 *
 * jsdom decodes no PNGs, so the decode path is driven with a stubbed `Image` and a stubbed
 * 2D context. The assertion is on the alpha channel actually written back.
 */
describe('mask background', () => {
  /** Pixel class indices in, the RGBA buffer the overlay paints out. */
  function paint(classNames: readonly string[], values: readonly number[]): Uint8ClampedArray {
    const data = new Uint8ClampedArray(values.length * 4);
    values.forEach((value, index) => {
      data[index * 4] = value;
      data[index * 4 + 1] = value;
      data[index * 4 + 2] = value;
      data[index * 4 + 3] = 255;
    });
    const buffer = { data, width: values.length, height: 1 };

    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage: () => undefined,
      getImageData: () => buffer,
      putImageData: () => undefined,
    } as unknown as CanvasRenderingContext2D);

    class LoadsImmediately {
      onload: (() => void) | null = null;
      set src(_value: string) {
        this.onload?.();
      }
    }
    vi.stubGlobal('Image', LoadsImmediately);

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

    return data;
  }

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('leaves a named background transparent', () => {
    const painted = paint(['background', 'sky'], [0, 1, 0]);

    expect(painted[3]).toBe(0);
    expect(painted[7]).toBe(255);
    expect(painted[11]).toBe(0);
  });

  it('paints class 0 when it is a real class, as ADE20k’s wall is', () => {
    const painted = paint(['wall', 'sky'], [0, 1]);

    expect(painted[3]).toBe(255);
    expect(painted[7]).toBe(255);
  });
});
