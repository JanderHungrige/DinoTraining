/**
 * The segmentations on the Studio canvas (doc 61).
 *
 * A sibling of the box overlay rather than part of it: `AnnotationCanvas` was already at
 * the project's 300-line gate, and the two draw in genuinely different ways — a box is a
 * positioned `<button>`, a mask is decoded pixels.
 *
 * **One canvas for every mask, not one canvas each.** The first version stacked an
 * absolutely-positioned full-resolution canvas per annotation, which is 15.8 MB of pixel
 * buffer apiece at 2464x1600: thirty chess pieces would have asked the compositor for
 * roughly half a gigabyte and stacked thirty translucent layers, so overlapping masks
 * darkened each other and the whole thing got muddy. Compositing into a single buffer is
 * cheaper *and* truer — where two masks meet, the later one wins outright, which is the
 * same last-writer-wins the backend's own index map produces.
 *
 * **Painting only.** Every mask's hit target is still the box button `AnnotationCanvas`
 * renders over it — doc 28's rule, reused rather than re-decided: mask pixels are awkward
 * to click and impossible to focus, and the derived rect gives keyboard operation, the
 * 1/2/3 verdict keys and the accessibility tree for free. So this layer is
 * `pointer-events: none` and carries no ARIA of its own.
 *
 * Tinted by **verdict**, in the same three colours the box borders use.
 */

import { useEffect, useRef, type JSX } from 'react';

import { decodeMap } from '../lib/decodeMap';
import type { RenderedImage } from '../lib/geometry';
import type { NumberedBox } from '../lib/boxReview';
import type { CanvasBox, Label } from '../types/annotation';
import type { Rgb } from '../lib/overlayPalette';

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
 * How opaque a mask's pixels are. The selected one is brighter rather than outlined: an
 * outline would compete with the box button's own focus ring, drawn directly on top.
 */
const ALPHA = 115;
const ALPHA_SELECTED = 190;

/**
 * A pixel belongs to the object when it is nearer 255 than 0.
 *
 * **Not `value > 0`.** These masks are encoded 0/255, and a browser that colour-manages
 * the PNG on the way in can turn a 0 into a 1 in a dither pattern — which `> 0` promotes
 * to a fully painted pixel, speckling the entire frame. `decodeMap` stops the conversion
 * happening; this makes the result not matter if some browser does it anyway.
 */
const FOREGROUND = 128;

export function MaskLayer({
  boxes,
  hidden,
  rendered,
  selectedId,
}: MaskLayerProps): JSX.Element | null {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const segmented = boxes
    .map(({ box }) => box)
    .filter((box) => box.mask !== undefined && !hidden.has(box.id));

  // The frame every mask's RLE covers. They all describe the same image, so the first
  // one's size is the canvas size.
  const first = segmented[0]?.mask?.rle.size;
  const height = first?.[0] ?? 0;
  const width = first?.[1] ?? 0;

  // Keyed on what actually changes the picture. Without the ids and verdicts in here a
  // relabel would leave the old colour on screen; with the whole box objects in here it
  // would re-decode every mask on every render.
  const signature = segmented
    .map((box) => `${box.id}:${box.label}:${box.id === selectedId ? 1 : 0}`)
    .join('|');

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || width <= 0 || height <= 0) return;
    let cancelled = false;

    void (async () => {
      const context = canvas.getContext('2d', { colorSpace: 'srgb' });
      if (!context) return;
      const composite = context.createImageData(width, height);
      const pixels = composite.data;

      for (const box of segmented) {
        const mask = box.mask;
        if (!mask) continue;
        const decoded = await decodeMap(mask.png, width, height);
        if (cancelled) return;
        if (!decoded) continue;

        const { r, g, b } = VERDICT_RGB[box.label];
        const alpha = box.id === selectedId ? ALPHA_SELECTED : ALPHA;
        for (let p = 0, i = 0; p < decoded.values.length; p += 1, i += 4) {
          if ((decoded.values[p] ?? 0) < FOREGROUND) continue;
          pixels[i] = r;
          pixels[i + 1] = g;
          pixels[i + 2] = b;
          pixels[i + 3] = alpha;
        }
      }

      if (cancelled) return;
      context.putImageData(composite, 0, 0);
    })();

    return () => {
      cancelled = true;
    };
    // `segmented` is rebuilt every render; `signature` is what says the picture changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, width, height]);

  if (segmented.length === 0) return null;

  return (
    <canvas
      ref={canvasRef}
      className="masklayer"
      width={width}
      height={height}
      aria-hidden="true"
      style={{
        left: `${rendered.offsetX}px`,
        top: `${rendered.offsetY}px`,
        width: `${rendered.width}px`,
        height: `${rendered.height}px`,
      }}
    />
  );
}

/** Exported for the tests: which annotations this layer will paint. */
export function paintable(
  boxes: readonly NumberedBox[],
  hidden: ReadonlySet<string>,
): readonly CanvasBox[] {
  return boxes
    .map(({ box }) => box)
    .filter((box) => box.mask !== undefined && !hidden.has(box.id));
}
