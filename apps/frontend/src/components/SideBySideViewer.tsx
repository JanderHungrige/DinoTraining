/**
 * Original and result, side by side, moving together.
 *
 * **Layout only.** This component does not know what a head produces — no boxes, masks,
 * depth or labels appear anywhere in it. Feature 20 draws those through `renderOverlay`,
 * which receives the image's *rendered* geometry so its marks land on the pixels rather
 * than on the letterbox.
 *
 * Both panes render the same transform object, so they cannot drift apart.
 */

import { useCallback, useEffect, useRef, useState, type JSX, type ReactNode } from 'react';

import { fitContain, type RenderedImage } from '../lib/geometry';
import { PAN_STEP, ZOOM_STEP, useViewTransform } from '../hooks/useViewTransform';

export interface SideBySideViewerProps {
  readonly imageUrl: string;
  readonly imageAlt: string;
  /**
   * Natural size, when the caller already knows it. Left out, the viewer measures it
   * from the image itself on load — so a caller that only has a URL needs no hidden
   * probe image of its own.
   */
  readonly naturalWidth?: number;
  readonly naturalHeight?: number;
  /** Drawn over the result pane, inside the shared transform. */
  readonly renderOverlay?: (rendered: RenderedImage) => ReactNode;
  /** Shown in the result pane before anything has run. */
  readonly resultPlaceholder?: ReactNode;
  readonly resultLabel?: string;
}

const EMPTY_SIZE = { width: 0, height: 0 };

export function SideBySideViewer({
  imageUrl,
  imageAlt,
  naturalWidth = 0,
  naturalHeight = 0,
  renderOverlay,
  resultPlaceholder,
  resultLabel = 'Result',
}: SideBySideViewerProps): JSX.Element {
  const view = useViewTransform();
  const frameRef = useRef<HTMLDivElement | null>(null);
  const [box, setBox] = useState(EMPTY_SIZE);
  // Measured from the image, used only when the caller did not supply a size. Stored as
  // the fallback rather than seeding from the props, which arrive before the image does.
  const [measured, setMeasured] = useState(EMPTY_SIZE);
  const dragging = useRef<{ x: number; y: number } | null>(null);

  // The clamp needs the *pane frame's* size, not the component's. Measuring the outer
  // element instead gives bounds about twice too generous — the image can then be
  // dragged off its own frame, which is the exact failure the clamp exists to prevent.
  // Both panes are the same size, so measuring one is enough.
  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;

    const measure = (): void => {
      const next = { width: frame.clientWidth, height: frame.clientHeight };
      setBox(next);
      view.setSize(next);
    };
    measure();

    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(measure);
    observer.observe(frame);
    return () => observer.disconnect();
  }, [view.setSize]);

  const rendered = fitContain(
    box.width,
    box.height,
    naturalWidth || measured.width,
    naturalHeight || measured.height,
  );

  const reportNaturalSize = useCallback((image: HTMLImageElement): void => {
    setMeasured((current) =>
      current.width === image.naturalWidth && current.height === image.naturalHeight
        ? current
        : { width: image.naturalWidth, height: image.naturalHeight },
    );
  }, []);

  const handleWheel = useCallback(
    (event: React.WheelEvent<HTMLDivElement>): void => {
      const frame = event.currentTarget.getBoundingClientRect();
      view.zoomAtPoint(
        event.clientX - frame.left,
        event.clientY - frame.top,
        event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP,
      );
    },
    [view],
  );

  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>): void => {
    dragging.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLDivElement>): void => {
    const from = dragging.current;
    if (!from) return;
    view.pan(event.clientX - from.x, event.clientY - from.y);
    dragging.current = { x: event.clientX, y: event.clientY };
  };

  const handlePointerUp = (event: React.PointerEvent<HTMLDivElement>): void => {
    dragging.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>): void => {
    const handled = true;
    switch (event.key) {
      case '+':
      case '=':
        view.zoomBy(ZOOM_STEP);
        break;
      case '-':
        view.zoomBy(1 / ZOOM_STEP);
        break;
      case '0':
        view.reset();
        break;
      case 'ArrowLeft':
        view.pan(PAN_STEP, 0);
        break;
      case 'ArrowRight':
        view.pan(-PAN_STEP, 0);
        break;
      case 'ArrowUp':
        view.pan(0, PAN_STEP);
        break;
      case 'ArrowDown':
        view.pan(0, -PAN_STEP);
        break;
      default:
        return;
    }
    if (handled) event.preventDefault();
  };

  const pane = (
    label: string,
    /** Inside the transform — it belongs to the image and must scale with it. */
    overlay: ReactNode,
    /** Outside the transform — chrome, which must not zoom. */
    chrome: ReactNode,
    measureThis: boolean,
  ): JSX.Element => (
    <figure className="viewer__pane">
      <figcaption className="viewer__label">{label}</figcaption>
      {/* The gestures live on the frame, not the component: the frame is the box the
          clamp is computed against, and a double-click on the controls must not reset
          the view. Both frames drive the one transform, so either pane can be dragged. */}
      <div
        className="viewer__frame"
        data-testid="viewer-frame"
        ref={measureThis ? frameRef : undefined}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        onDoubleClick={view.reset}
      >
        <div className="viewer__stage" data-testid="viewer-stage" style={{ transform: view.css }}>
          <img
            className="viewer__img"
            src={imageUrl}
            alt={imageAlt}
            draggable={false}
            onLoad={(event) => reportNaturalSize(event.currentTarget)}
          />
          {overlay}
        </div>
        {chrome}
      </div>
    </figure>
  );

  return (
    <div
      className="viewer"
      role="group"
      aria-label="Image comparison"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      <div className="viewer__panes">
        {pane('Original', null, null, true)}
        {pane(
          resultLabel,
          renderOverlay ? renderOverlay(rendered) : null,
          renderOverlay ? null : resultPlaceholder,
          false,
        )}
      </div>

      <div className="viewer__controls">
        <button
          type="button"
          className="btn"
          onClick={() => view.zoomBy(1 / ZOOM_STEP)}
          disabled={!view.canZoomOut}
        >
          Zoom out
        </button>
        <span className="viewer__zoom">{view.percent}%</span>
        <button
          type="button"
          className="btn"
          onClick={() => view.zoomBy(ZOOM_STEP)}
          disabled={!view.canZoomIn}
        >
          Zoom in
        </button>
        <button type="button" className="btn" onClick={view.reset}>
          Reset
        </button>
        <span className="viewer__hint">Drag to pan · arrows and +/− work too</span>
      </div>
    </div>
  );
}
