/**
 * The mask layer (doc 61).
 *
 * Two properties matter and neither is "a mask renders". The first is that this layer
 * never takes a pointer or an accessibility-tree entry — the box button drawn over each
 * mask is the hit target, and a second announcement would put two entries in the tree for
 * one annotation. The second is that it honours the same hiding rules as the boxes, or the
 * threshold slider would leave masks on screen for annotations it had filtered out.
 */

import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { numbered } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';
import type { RenderedImage } from '../lib/geometry';
import { MaskLayer } from './MaskLayer';

const RENDERED: RenderedImage = {
  width: 400,
  height: 300,
  offsetX: 10,
  offsetY: 20,
  naturalWidth: 800,
  naturalHeight: 600,
};

function box(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return { id, label: 'positive', provenance: 'hand-drawn', x: 0, y: 0, w: 10, h: 10, ...over };
}

function segmented(id: string, over: Partial<CanvasBox> = {}): CanvasBox {
  return box(id, {
    provenance: 'grounded-sam',
    mask: { rle: { size: [600, 800], counts: [1, 2] }, png: 'iVBOR' },
    ...over,
  });
}

function renderLayer(boxes: CanvasBox[], hidden = new Set<string>(), selectedId: string | null = null) {
  return render(
    <MaskLayer
      boxes={numbered(boxes)}
      hidden={hidden}
      rendered={RENDERED}
      selectedId={selectedId}
    />,
  );
}

describe('what it draws', () => {
  it('draws nothing at all when no annotation has a mask', () => {
    // Not an empty div: a layer over the image with nothing in it is still a layer, and
    // this one is `position: absolute; inset: 0`.
    const { container } = renderLayer([box('a'), box('b')]);

    expect(container.querySelector('.masklayer')).toBeNull();
  });

  it('draws one canvas per segmented annotation', () => {
    const { container } = renderLayer([segmented('a'), box('b'), segmented('c')]);

    expect(container.querySelectorAll('canvas')).toHaveLength(2);
  });

  it('sizes each canvas from the RLE, which is height-first', () => {
    // COCO's `size` is [height, width] — the reverse of every other size in the app.
    // Getting this backwards renders the mask transposed and silently wrong.
    const { container } = renderLayer([segmented('a')]);
    const canvas = container.querySelector('canvas') as HTMLCanvasElement;

    expect(canvas.width).toBe(800);
    expect(canvas.height).toBe(600);
  });

  it('places the layer over the rendered image, not the container', () => {
    // An object-fit:contain image is letterboxed; MapOverlay positions each canvas by the
    // rendered geometry, which is what keeps a mask on its object.
    const { container } = renderLayer([segmented('a')]);
    const canvas = container.querySelector('canvas') as HTMLElement;

    expect(canvas.style.left).toBe('10px');
    expect(canvas.style.top).toBe('20px');
    expect(canvas.style.width).toBe('400px');
  });
});

describe('what it refuses to do', () => {
  it('takes no pointer events', () => {
    // The box button over each mask is the hit target. A layer that intercepted clicks
    // would take the verdict cycle and the drawing gesture with it.
    const { container } = renderLayer([segmented('a')]);

    expect(container.querySelector('.masklayer')).toHaveAttribute('aria-hidden', 'true');
  });

  it('adds nothing to the accessibility tree', () => {
    // Each annotation is announced once, by its button. Announcing the mask too would
    // give a screen-reader user two entries for one thing.
    const { container } = renderLayer([segmented('a')]);

    expect(container.querySelectorAll('[role="img"]')).toHaveLength(0);
  });
});

describe('hiding', () => {
  it('does not draw a mask the threshold is hiding', () => {
    // Otherwise lowering the cutoff would leave masks on screen for annotations the list
    // says are filtered out.
    const { container } = renderLayer([segmented('a'), segmented('b')], new Set(['a']));

    expect(container.querySelectorAll('canvas')).toHaveLength(1);
  });

  it('draws nothing when every mask is hidden', () => {
    const { container } = renderLayer([segmented('a')], new Set(['a']));

    expect(container.querySelector('.masklayer')).toBeNull();
  });
});

describe('selection', () => {
  it('brightens the selected mask rather than outlining it', () => {
    // An outline would compete with the box button's own focus ring, drawn directly on top.
    const { container } = renderLayer([segmented('a'), segmented('b')], new Set(), 'a');
    const [first, second] = [...container.querySelectorAll('canvas')] as HTMLElement[];

    expect(Number(first?.style.opacity)).toBeGreaterThan(Number(second?.style.opacity));
  });
});
