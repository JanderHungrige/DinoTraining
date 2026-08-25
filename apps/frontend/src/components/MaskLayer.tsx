/**
 * The segmentations on the Studio canvas (doc 61).
 *
 * A sibling of the box overlay rather than part of it, for the reason `AnnotationCanvas`
 * was already at 292 lines against the project's 300-line gate — and because the two draw
 * in genuinely different ways: a box is a positioned `<button>`, a mask is decoded pixels
 * on a `<canvas>`.
 *
 * **Painting only.** Every mask's hit target is still the box button `AnnotationCanvas`
 * renders over it, which is doc 28's rule reused rather than re-decided: mask pixels are
 * awkward to click and impossible to focus, and the derived rect gives keyboard operation,
 * the 1/2/3 verdict keys and the accessibility tree for free. So this layer is
 * `pointer-events: none` and carries no ARIA of its own — announcing each mask here would
 * put two entries in the accessibility tree for one annotation.
 *
 * Tinted by **verdict**, in the same three colours the box borders use, so one legend
 * serves the whole surface.
 */

import type { JSX } from 'react';

import type { RenderedImage } from '../lib/geometry';
import type { NumberedBox } from '../lib/boxReview';
import type { Label } from '../types/annotation';
import type { Rgb } from '../lib/overlayPalette';
import { MapOverlay } from './overlays/MapOverlay';

export interface MaskLayerProps {
  /** Every box; the ones with no mask are skipped here and drawn as rects as always. */
  readonly boxes: readonly NumberedBox[];
  readonly hidden: ReadonlySet<string>;
  readonly rendered: RenderedImage;
  readonly selectedId: string | null;
}

/** Matching `.canvas__box--<label>`, so a mask and a box of the same verdict agree. */
const VERDICT_RGB: Readonly<Record<Label, Rgb>> = Object.freeze({
  positive: { r: 74, g: 222, b: 128 },
  negative: { r: 248, g: 113, b: 113 },
  unclear: { r: 251, g: 191, b: 36 },
});

/**
 * Background transparent, object opaque.
 *
 * Module-level so its identity is stable: `MapOverlay` keys its decode effect on this
 * function, and a fresh closure per render would re-decode every mask on every render.
 */
function objectOnly(value: number): number {
  return value > 0 ? 255 : 0;
}

/** One stable colour function per verdict, for the same reason. */
const COLOUR_FOR: Readonly<Record<Label, (value: number) => Rgb>> = Object.freeze({
  positive: () => VERDICT_RGB.positive,
  negative: () => VERDICT_RGB.negative,
  unclear: () => VERDICT_RGB.unclear,
});

export function MaskLayer({
  boxes,
  hidden,
  rendered,
  selectedId,
}: MaskLayerProps): JSX.Element | null {
  const segmented = boxes.filter(
    ({ box }) => box.mask !== undefined && !hidden.has(box.id),
  );
  if (segmented.length === 0) return null;

  return (
    <div className="masklayer" aria-hidden="true">
      {segmented.map(({ box }) => (
        <MapOverlay
          key={box.id}
          encoded={box.mask?.png ?? ''}
          width={box.mask?.rle.size[1] ?? 0}
          height={box.mask?.rle.size[0] ?? 0}
          rendered={rendered}
          colourFor={COLOUR_FOR[box.label]}
          alphaFor={objectOnly}
          // The selected mask is brighter rather than outlined: an outline would compete
          // with the box button's own focus ring drawn directly on top of it.
          opacity={box.id === selectedId ? 0.75 : 0.45}
        />
      ))}
    </div>
  );
}
