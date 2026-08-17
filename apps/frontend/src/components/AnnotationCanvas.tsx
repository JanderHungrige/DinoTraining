/**
 * Image with an overlay of labelled boxes.
 *
 * DOM overlay rather than <canvas>: each box is a real focusable button, so keyboard
 * operation, focus rings and the accessibility tree come for free. A canvas would
 * need all three rebuilt by hand, and at the tens of boxes this app produces there is
 * no performance reason to pay that.
 *
 * Controlled component — it emits a new array and the parent owns the state.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type JSX,
  type KeyboardEvent,
  type PointerEvent,
} from 'react';

import {
  fitContain,
  isDeliberateDrag,
  rectFromPoints,
  toDisplay,
  toNatural,
  type Rect,
  type RenderedImage,
} from '../lib/geometry';
import { LABEL_TITLES, nextLabel, type CanvasBox, type Label } from '../types/annotation';

export interface AnnotationCanvasProps {
  readonly imageUrl: string;
  readonly naturalWidth: number;
  readonly naturalHeight: number;
  readonly boxes: readonly CanvasBox[];
  readonly selectedId: string | null;
  readonly onBoxesChange: (boxes: CanvasBox[]) => void;
  readonly onSelect: (id: string | null) => void;
  readonly disabled?: boolean;
}

const EMPTY_RENDER: RenderedImage = {
  width: 0,
  height: 0,
  offsetX: 0,
  offsetY: 0,
  naturalWidth: 0,
  naturalHeight: 0,
};

function makeId(): string {
  return `box-${Math.random().toString(36).slice(2, 10)}`;
}

function labelFromKey(key: string): Label | null {
  switch (key) {
    case '1':
    case 'p':
      return 'positive';
    case '2':
    case 'n':
      return 'negative';
    case '3':
    case 'u':
      return 'unclear';
    default:
      return null;
  }
}

export function AnnotationCanvas({
  imageUrl,
  naturalWidth,
  naturalHeight,
  boxes,
  selectedId,
  onBoxesChange,
  onSelect,
  disabled = false,
}: AnnotationCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [rendered, setRendered] = useState<RenderedImage>(EMPTY_RENDER);
  const [draft, setDraft] = useState<Rect | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  // The live rect also lives in a ref: pointerup must not depend on a state update
  // from pointermove having been flushed, which is not guaranteed between events.
  const dragRect = useRef<Rect | null>(null);

  const measure = useCallback((): void => {
    const node = containerRef.current;
    if (!node) return;
    const { width, height } = node.getBoundingClientRect();
    setRendered(fitContain(width, height, naturalWidth, naturalHeight));
  }, [naturalWidth, naturalHeight]);

  // Re-measure on resize: the letterboxing changes with the container, and a stale
  // measurement puts every box in the wrong place.
  useEffect(() => {
    measure();
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === 'undefined') return;

    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [measure]);

  const setLabel = useCallback(
    (id: string, label: Label): void => {
      onBoxesChange(boxes.map((box) => (box.id === id ? { ...box, label } : box)));
    },
    [boxes, onBoxesChange],
  );

  const removeBox = useCallback(
    (id: string): void => {
      onBoxesChange(boxes.filter((box) => box.id !== id));
      onSelect(null);
    },
    [boxes, onBoxesChange, onSelect],
  );

  const handleBoxKeyDown = (event: KeyboardEvent<HTMLButtonElement>, box: CanvasBox): void => {
    if (disabled) return;

    const label = labelFromKey(event.key.toLowerCase());
    if (label) {
      event.preventDefault();
      setLabel(box.id, label);
      return;
    }
    if (event.key === 'Delete' || event.key === 'Backspace') {
      event.preventDefault();
      removeBox(box.id);
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      onSelect(null);
    }
  };

  const localPoint = (event: PointerEvent<HTMLDivElement>): { x: number; y: number } => {
    const node = containerRef.current;
    if (!node) return { x: 0, y: 0 };
    const bounds = node.getBoundingClientRect();
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  };

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>): void => {
    // Only a drag starting on empty space draws; a press on a box is that box's click.
    if (disabled || event.target !== event.currentTarget || event.button !== 0) return;
    const point = localPoint(event);
    dragStart.current = point;
    dragRect.current = { x: point.x, y: point.y, w: 0, h: 0 };
    setDraft(dragRect.current);
    event.currentTarget.setPointerCapture?.(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>): void => {
    const start = dragStart.current;
    if (!start) return;
    const point = localPoint(event);
    dragRect.current = rectFromPoints(start.x, start.y, point.x, point.y);
    setDraft(dragRect.current);
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>): void => {
    const start = dragStart.current;
    const current = dragRect.current;
    dragStart.current = null;
    dragRect.current = null;
    setDraft(null);
    if (!start || !current) return;

    event.currentTarget.releasePointerCapture?.(event.pointerId);

    // A tiny drag is a stray click, not an attempt to draw a box.
    if (!isDeliberateDrag(current)) {
      onSelect(null);
      return;
    }

    const natural = toNatural(current, rendered);
    if (natural.w <= 0 || natural.h <= 0) return;

    const created: CanvasBox = {
      id: makeId(),
      label: 'positive',
      provenance: 'hand-drawn',
      x: Math.round(natural.x),
      y: Math.round(natural.y),
      w: Math.round(natural.w),
      h: Math.round(natural.h),
    };
    onBoxesChange([...boxes, created]);
    onSelect(created.id);
  };

  return (
    <div className="canvas">
      <div
        ref={containerRef}
        className="canvas__stage"
        data-testid="canvas-stage"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <img
          className="canvas__image"
          src={imageUrl}
          alt=""
          draggable={false}
          onLoad={measure}
        />

        {boxes.map((box) => {
          const rect = toDisplay(box, rendered);
          const selected = box.id === selectedId;
          const score = box.score === undefined ? '' : `, score ${(box.score * 100).toFixed(0)}%`;
          return (
            <button
              key={box.id}
              type="button"
              className={`canvas__box canvas__box--${box.label}${selected ? ' canvas__box--selected' : ''}`}
              style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
              aria-pressed={selected}
              aria-label={`${LABEL_TITLES[box.label]} box${box.text ? `: ${box.text}` : ''}${score}. Press 1, 2 or 3 to relabel, Delete to remove.`}
              disabled={disabled}
              onClick={() => {
                onSelect(box.id);
                setLabel(box.id, nextLabel(box.label));
              }}
              onFocus={() => onSelect(box.id)}
              onKeyDown={(event) => handleBoxKeyDown(event, box)}
            >
              <span className="canvas__boxtag">
                {LABEL_TITLES[box.label]}
                {box.score !== undefined ? ` ${(box.score * 100).toFixed(0)}%` : ''}
              </span>
            </button>
          );
        })}

        {draft && (
          <div
            className="canvas__draft"
            style={{ left: draft.x, top: draft.y, width: draft.w, height: draft.h }}
            aria-hidden="true"
          />
        )}
      </div>

      <p className="canvas__hint">
        Drag on the image to draw a box. Click a box to cycle its label. With a box
        focused: <kbd>1</kbd> positive, <kbd>2</kbd> negative, <kbd>3</kbd> unclear,{' '}
        <kbd>Delete</kbd> to remove.
      </p>
    </div>
  );
}
