/**
 * Zoom-and-pan arithmetic, with no React in front of it.
 *
 * The interesting cases here — zoom about a point, and the clamp that keeps content on
 * screen — are pure arithmetic, and they are exactly the parts that are painful to debug
 * through a rendered component. Kept separate so they can be tested as numbers.
 */

import { clamp } from './geometry';

export interface ViewTransform {
  /** 1 = fit. The image is never drawn smaller than its container. */
  readonly scale: number;
  /** Container-pixel translation, applied before scale. */
  readonly tx: number;
  readonly ty: number;
}

export interface ViewSize {
  readonly width: number;
  readonly height: number;
}

export const MIN_SCALE = 1;
export const MAX_SCALE = 8;

export const IDENTITY: ViewTransform = { scale: MIN_SCALE, tx: 0, ty: 0 };

/**
 * Keep the scaled content covering the container.
 *
 * With container width `W` and scale `s` the content is `W·s` wide, so `tx` may run from
 * `W(1−s)` to `0`. At `s = 1` that collapses to `tx = 0`, which is why panning a fitted
 * image correctly does nothing rather than needing a special case.
 *
 * Without this the user drags the image off-screen and is left staring at an empty pane
 * with no obvious way back.
 */
export function clampTransform(transform: ViewTransform, size: ViewSize): ViewTransform {
  const scale = clamp(transform.scale, MIN_SCALE, MAX_SCALE);
  return {
    scale,
    tx: clamp(transform.tx, size.width * (1 - scale), 0),
    ty: clamp(transform.ty, size.height * (1 - scale), 0),
  };
}

/**
 * Zoom about a container-relative point, keeping the pixel under it in place.
 *
 * Zooming about the centre instead is what makes a viewer feel broken: the user points
 * at a detail and it slides away from the cursor.
 */
export function zoomAt(
  transform: ViewTransform,
  focusX: number,
  focusY: number,
  factor: number,
  size: ViewSize,
): ViewTransform {
  const scale = clamp(transform.scale * factor, MIN_SCALE, MAX_SCALE);
  // The image-space point under the focus must map back to the same focus point:
  //   (focus - tx) / scale  is invariant, so  tx' = focus - (focus - tx) · scale'/scale
  const ratio = scale / transform.scale;

  return clampTransform(
    {
      scale,
      tx: focusX - (focusX - transform.tx) * ratio,
      ty: focusY - (focusY - transform.ty) * ratio,
    },
    size,
  );
}

export function panBy(
  transform: ViewTransform,
  dx: number,
  dy: number,
  size: ViewSize,
): ViewTransform {
  return clampTransform(
    { scale: transform.scale, tx: transform.tx + dx, ty: transform.ty + dy },
    size,
  );
}

/** CSS for a transform. `translate` before `scale` — the order the maths assumes. */
export function toCss(transform: ViewTransform): string {
  return `translate(${transform.tx}px, ${transform.ty}px) scale(${transform.scale})`;
}
