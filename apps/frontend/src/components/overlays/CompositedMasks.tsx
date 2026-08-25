/**
 * Several binary masks painted into **one** canvas, tinted by verdict.
 *
 * Shared by the Annotation Studio's `MaskLayer` and the Dataset Generator's
 * `MaskReviewCanvas`. Both had grown their own version, and both had the same three faults
 * — which is the argument for one implementation rather than two.
 *
 * **One buffer, not one per mask.** A full-resolution canvas is 15.8 MB at 2464x1600, so a
 * folder run with twenty masks asked the compositor for around 300 MB and stacked twenty
 * translucent layers that darkened every overlap. Compositing is cheaper *and* truer: where
 * two masks meet the later one wins outright, which is the same last-writer-wins the
 * backend's own index map produces.
 *
 * **A pixel belongs to the object when it is nearer 255 than 0 — never `> 0`.** These masks
 * are encoded 0/255, and WebKit colour-manages the PNG on the way in whatever
 * `colorSpaceConversion: 'none'` asks of it, dithering the low bits. `> 0` promotes every
 * dithered 0 to a fully painted pixel and speckles the entire frame; that was the green
 * fizzle, reported twice, in two different surfaces, for exactly this reason.
 *
 * **Painting only.** Every mask's hit target is the button its caller draws over it — mask
 * pixels are awkward to click and impossible to focus. So this is `pointer-events: none`
 * and `aria-hidden`: the buttons already carry the verdict, the concept and the score, and
 * announcing the mask again would give a screen-reader user two entries for one thing.
 */

import { useEffect, useRef, type JSX } from 'react';

import { decodeMap } from '../../lib/decodeMap';
import type { RenderedImage } from '../../lib/geometry';
import type { Label } from '../../types/annotation';
import type { Rgb } from '../../lib/overlayPalette';

/** The least a mask has to be to get painted. */
export interface PaintedMask {
  readonly id: string;
  readonly label: Label;
  /** Base64 PNG, no data: prefix. 0 = background, 255 = this object. */
  readonly png: string;
}

export interface CompositedMasksProps {
  readonly masks: readonly PaintedMask[];
  /** The frame every mask covers, in natural image pixels. */
  readonly width: number;
  readonly height: number;
  readonly rendered: RenderedImage;
  readonly selectedId: string | null;
  readonly className?: string;
}

/** Matching `.canvas__box--<label>`, so a mask and a box of the same verdict agree. */
const VERDICT_RGB: Readonly<Record<Label, Rgb>> = Object.freeze({
  positive: { r: 74, g: 222, b: 128 },
  negative: { r: 248, g: 113, b: 113 },
  unclear: { r: 251, g: 191, b: 36 },
});

/**
 * How opaque a mask's pixels are. The selected one is brighter rather than outlined: an
 * outline would compete with the button's own focus ring, drawn directly on top of it.
 */
const ALPHA = 115;
const ALPHA_SELECTED = 190;

/** See the note at the top of the file. This is the defence that does not depend on a
 *  browser honouring a flag. */
const FOREGROUND = 128;

export function CompositedMasks({
  masks,
  width,
  height,
  rendered,
  selectedId,
  className = 'masklayer',
}: CompositedMasksProps): JSX.Element | null {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Keyed on what actually changes the picture. Without the ids and verdicts a relabel
  // would leave the old colour on screen; with the mask objects themselves it would
  // re-decode every PNG on every render.
  const signature = masks
    .map((mask) => `${mask.id}:${mask.label}:${mask.id === selectedId ? 1 : 0}`)
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

      for (const mask of masks) {
        const decoded = await decodeMap(mask.png, width, height);
        if (cancelled) return;
        if (!decoded) continue;

        const { r, g, b } = VERDICT_RGB[mask.label];
        const alpha = mask.id === selectedId ? ALPHA_SELECTED : ALPHA;
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
    // `masks` is rebuilt every render; `signature` is what says the picture changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature, width, height]);

  if (masks.length === 0) return null;

  // Positioned on the *rendered* image rather than the container: an object-fit:contain
  // image is letterboxed, and using the container would offset every mask by the letterbox.
  return (
    <canvas
      ref={canvasRef}
      className={className}
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
