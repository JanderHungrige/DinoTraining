/**
 * One zoom/pan state, however many panes render it.
 *
 * The obvious alternative — a transform per pane, kept in step by events — produces
 * feedback loops, needs an "is this echo mine?" guard, and drifts by a rounding error
 * per event until the panes visibly disagree. There is nothing to keep in step here.
 */

import { useCallback, useRef, useState } from 'react';

import {
  IDENTITY,
  MAX_SCALE,
  MIN_SCALE,
  panBy,
  toCss,
  zoomAt,
  type ViewSize,
  type ViewTransform,
} from '../lib/viewTransform';

/** One wheel notch, or one press of the zoom button. */
export const ZOOM_STEP = 1.25;
/** One arrow-key press, in container pixels. */
export const PAN_STEP = 40;

export interface ViewTransformState {
  readonly transform: ViewTransform;
  readonly css: string;
  /** Whole-percent zoom, for display. */
  readonly percent: number;
  readonly canZoomIn: boolean;
  readonly canZoomOut: boolean;
  /** Container size the clamp is computed against; set by the component on layout. */
  readonly setSize: (size: ViewSize) => void;
  readonly zoomAtPoint: (focusX: number, focusY: number, factor: number) => void;
  readonly zoomBy: (factor: number) => void;
  readonly pan: (dx: number, dy: number) => void;
  readonly reset: () => void;
}

export function useViewTransform(): ViewTransformState {
  const [transform, setTransform] = useState<ViewTransform>(IDENTITY);
  // A ref, not state: the size is an input to the maths, never something to render on,
  // and putting it in state would re-render every pane on each resize observation.
  const size = useRef<ViewSize>({ width: 0, height: 0 });

  const setSize = useCallback((next: ViewSize): void => {
    size.current = next;
  }, []);

  const zoomAtPoint = useCallback((focusX: number, focusY: number, factor: number): void => {
    setTransform((current) => zoomAt(current, focusX, focusY, factor, size.current));
  }, []);

  const zoomBy = useCallback((factor: number): void => {
    // No pointer involved, so zoom about the middle of the container.
    setTransform((current) =>
      zoomAt(current, size.current.width / 2, size.current.height / 2, factor, size.current),
    );
  }, []);

  const pan = useCallback((dx: number, dy: number): void => {
    setTransform((current) => panBy(current, dx, dy, size.current));
  }, []);

  const reset = useCallback((): void => setTransform(IDENTITY), []);

  return {
    transform,
    css: toCss(transform),
    percent: Math.round(transform.scale * 100),
    canZoomIn: transform.scale < MAX_SCALE,
    canZoomOut: transform.scale > MIN_SCALE,
    setSize,
    zoomAtPoint,
    zoomBy,
    pan,
    reset,
  };
}
