/**
 * The segmentations on the Studio canvas (doc 61).
 *
 * An adapter, since the compositing moved to `CompositedMasks` — the Dataset Generator's
 * review surface had grown its own copy with the same three faults, and one implementation
 * of "paint these masks" is better than two that drift.
 *
 * What is left here is the Studio's own rule: an annotation carries its mask on itself, and
 * a hidden one is not painted. The hit target is still the box button `AnnotationCanvas`
 * renders over each mask — doc 28's rule, reused rather than re-decided.
 */

import type { JSX } from 'react';

import type { RenderedImage } from '../lib/geometry';
import type { NumberedBox } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';
import { CompositedMasks, type PaintedMask } from './overlays/CompositedMasks';

export interface MaskLayerProps {
  /** Every box; the ones with no mask are skipped here and drawn as rects as always. */
  readonly boxes: readonly NumberedBox[];
  readonly hidden: ReadonlySet<string>;
  readonly rendered: RenderedImage;
  readonly selectedId: string | null;
}

/** Which annotations this layer will paint. Exported for the tests. */
export function paintable(
  boxes: readonly NumberedBox[],
  hidden: ReadonlySet<string>,
): readonly CanvasBox[] {
  return boxes
    .map(({ box }) => box)
    .filter((box) => box.mask !== undefined && !hidden.has(box.id));
}

export function MaskLayer({
  boxes,
  hidden,
  rendered,
  selectedId,
}: MaskLayerProps): JSX.Element | null {
  const segmented = paintable(boxes, hidden);

  // The frame every mask's RLE covers. They all describe the same image, so the first
  // one's size is the canvas size.
  const size = segmented[0]?.mask?.rle.size;
  const painted: PaintedMask[] = segmented.map((box) => ({
    id: box.id,
    label: box.label,
    png: box.mask?.png ?? '',
  }));

  return (
    <CompositedMasks
      masks={painted}
      width={size?.[1] ?? 0}
      height={size?.[0] ?? 0}
      rendered={rendered}
      selectedId={selectedId}
    />
  );
}
