/**
 * Drawing a box by dragging on the canvas.
 *
 * Extracted from `AnnotationCanvas` when doc 61's mask layer pushed that file past the
 * project's 300-line gate, and the seam is a real one: everything here is about turning a
 * pointer gesture into one rectangle, and everything left there is about painting what
 * already exists.
 *
 * The guard in `onPointerDown` is load-bearing and was a shipped bug. It used to ask for
 * `event.target === event.currentTarget`, but the image fills the stage and is therefore
 * the target of every press inside it — so no drag ever started and drawing a box by hand
 * was impossible in the running app while every test passed. `.canvas__image` is
 * `pointer-events: none` now; the rule is *also* stated here as what it means, so a future
 * style change cannot silently take drawing away again.
 */

import { useCallback, useRef, useState, type PointerEvent } from 'react';

import {
  isDeliberateDrag,
  rectFromPoints,
  toNatural,
  type Rect,
  type RenderedImage,
} from '../lib/geometry';

export interface BoxDraw {
  /** The rectangle being dragged right now, for the dashed preview. Null when idle. */
  readonly draft: Rect | null;
  readonly onPointerDown: (event: PointerEvent<HTMLDivElement>) => void;
  readonly onPointerMove: (event: PointerEvent<HTMLDivElement>) => void;
  readonly onPointerUp: (event: PointerEvent<HTMLDivElement>) => void;
}

export interface BoxDrawOptions {
  readonly containerRef: React.RefObject<HTMLDivElement | null>;
  readonly rendered: RenderedImage;
  readonly disabled: boolean;
  /** A finished rectangle in natural image pixels. */
  readonly onDraw: (rect: Rect) => void;
  /** A press that turned out to be a stray click rather than a drag. */
  readonly onStrayClick: () => void;
}

export function useBoxDraw({
  containerRef,
  rendered,
  disabled,
  onDraw,
  onStrayClick,
}: BoxDrawOptions): BoxDraw {
  const [draft, setDraft] = useState<Rect | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  // The live rect also lives in a ref: pointerup must not depend on a state update from
  // pointermove having been flushed, which is not guaranteed between events.
  const dragRect = useRef<Rect | null>(null);

  const localPoint = useCallback(
    (event: PointerEvent<HTMLDivElement>): { x: number; y: number } => {
      const node = containerRef.current;
      if (!node) return { x: 0, y: 0 };
      const bounds = node.getBoundingClientRect();
      return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
    },
    [containerRef],
  );

  const onPointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>): void => {
      if (disabled || event.button !== 0) return;
      // A press on a box is that box's click; anything else on the stage draws.
      if ((event.target as HTMLElement).closest('button')) return;
      const point = localPoint(event);
      dragStart.current = point;
      dragRect.current = { x: point.x, y: point.y, w: 0, h: 0 };
      setDraft(dragRect.current);
      event.currentTarget.setPointerCapture?.(event.pointerId);
    },
    [disabled, localPoint],
  );

  const onPointerMove = useCallback(
    (event: PointerEvent<HTMLDivElement>): void => {
      const start = dragStart.current;
      if (!start) return;
      const point = localPoint(event);
      dragRect.current = rectFromPoints(start.x, start.y, point.x, point.y);
      setDraft(dragRect.current);
    },
    [localPoint],
  );

  const onPointerUp = useCallback(
    (event: PointerEvent<HTMLDivElement>): void => {
      const start = dragStart.current;
      const current = dragRect.current;
      dragStart.current = null;
      dragRect.current = null;
      setDraft(null);
      if (!start || !current) return;

      event.currentTarget.releasePointerCapture?.(event.pointerId);

      // A tiny drag is a stray click, not an attempt to draw a box.
      if (!isDeliberateDrag(current)) {
        onStrayClick();
        return;
      }

      const natural = toNatural(current, rendered);
      if (natural.w <= 0 || natural.h <= 0) return;
      onDraw(natural);
    },
    [rendered, onDraw, onStrayClick],
  );

  return { draft, onPointerDown, onPointerMove, onPointerUp };
}
