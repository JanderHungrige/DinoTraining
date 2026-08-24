/**
 * The only place that converts between displayed pixels and image-natural pixels.
 *
 * A second conversion site is how boxes end up subtly offset on scaled displays and
 * nobody can tell which of the two is wrong.
 */

/** How the image is laid out inside its container, after object-fit: contain. */
export interface RenderedImage {
  /** Displayed width/height of the image content itself (not the container). */
  readonly width: number;
  readonly height: number;
  /** Offset of the image content inside the container, from letterboxing. */
  readonly offsetX: number;
  readonly offsetY: number;
  readonly naturalWidth: number;
  readonly naturalHeight: number;
}

export interface Rect {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Work out where an `object-fit: contain` image actually sits in its container.
 *
 * The rendered content is letterboxed when the aspect ratios differ, so the container
 * box is not the image box — using the container would offset every annotation.
 */
export function fitContain(
  containerWidth: number,
  containerHeight: number,
  naturalWidth: number,
  naturalHeight: number,
): RenderedImage {
  if (naturalWidth <= 0 || naturalHeight <= 0 || containerWidth <= 0 || containerHeight <= 0) {
    return {
      width: 0,
      height: 0,
      offsetX: 0,
      offsetY: 0,
      naturalWidth: Math.max(naturalWidth, 0),
      naturalHeight: Math.max(naturalHeight, 0),
    };
  }

  const scale = Math.min(containerWidth / naturalWidth, containerHeight / naturalHeight);
  const width = naturalWidth * scale;
  const height = naturalHeight * scale;

  return {
    width,
    height,
    offsetX: (containerWidth - width) / 2,
    offsetY: (containerHeight - height) / 2,
    naturalWidth,
    naturalHeight,
  };
}

/** Image-natural pixels → displayed pixels, relative to the container. */
export function toDisplay(box: Rect, rendered: RenderedImage): Rect {
  if (rendered.naturalWidth <= 0 || rendered.naturalHeight <= 0) {
    return { x: 0, y: 0, w: 0, h: 0 };
  }
  const scaleX = rendered.width / rendered.naturalWidth;
  const scaleY = rendered.height / rendered.naturalHeight;

  return {
    x: box.x * scaleX + rendered.offsetX,
    y: box.y * scaleY + rendered.offsetY,
    w: box.w * scaleX,
    h: box.h * scaleY,
  };
}

/**
 * Displayed pixels → image-natural pixels, clamped to the image.
 *
 * Clamping here means a drag that leaves the frame still yields a valid box rather
 * than a 422 from the backend's bounds check.
 */
export function toNatural(rect: Rect, rendered: RenderedImage): Rect {
  if (rendered.width <= 0 || rendered.height <= 0) {
    return { x: 0, y: 0, w: 0, h: 0 };
  }
  const scaleX = rendered.naturalWidth / rendered.width;
  const scaleY = rendered.naturalHeight / rendered.height;

  const left = clamp((rect.x - rendered.offsetX) * scaleX, 0, rendered.naturalWidth);
  const top = clamp((rect.y - rendered.offsetY) * scaleY, 0, rendered.naturalHeight);
  const right = clamp((rect.x + rect.w - rendered.offsetX) * scaleX, 0, rendered.naturalWidth);
  const bottom = clamp((rect.y + rect.h - rendered.offsetY) * scaleY, 0, rendered.naturalHeight);

  return { x: left, y: top, w: right - left, h: bottom - top };
}

/** Turn two drag corners into a positive-area rect, whichever way it was dragged. */
export function rectFromPoints(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): Rect {
  return {
    x: Math.min(startX, endX),
    y: Math.min(startY, endY),
    w: Math.abs(endX - startX),
    h: Math.abs(endY - startY),
  };
}

/** Below this (displayed px) a drag is a stray click, not an attempt to draw. */
export const MIN_DRAG_PX = 5;

export function isDeliberateDrag(rect: Rect): boolean {
  return rect.w >= MIN_DRAG_PX && rect.h >= MIN_DRAG_PX;
}
