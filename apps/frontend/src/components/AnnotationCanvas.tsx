/**
 * Image with an overlay of numbered, labelled boxes.
 *
 * DOM overlay rather than <canvas>: each box is a real focusable button, so keyboard
 * operation, focus rings and the accessibility tree come for free. A canvas would
 * need all three rebuilt by hand, and at the tens of boxes this app produces there is
 * no performance reason to pay that.
 *
 * Controlled component — it emits a new array and the parent owns the state.
 *
 * **Paint order is by descending area** (doc 47). Every box is a button filling its own
 * rect, so a large box painted after a small one swallows every click meant for it — the
 * bug Jan reported. Smallest-on-top means a box that entirely contains another can never
 * hide it. The side list handles what no paint order can: partial overlap.
 *
 * Each box shows **its number and its class**, not its verdict. For detection output the
 * class is the thing being checked and the number is how the box is named in conversation
 * and in the list beside it; the verdict is legible from the colour.
 *
 * **Masks are painted by `MaskLayer`, and the box stays the hit target** (doc 61). An
 * annotation that carries a segmentation gets its mask drawn and its rect hidden unless
 * the view asks for boxes — the mask is the finer answer, and the rect is derivable from
 * it. The button is still there either way, transparent but focusable, because mask pixels
 * cannot be focused and every keyboard affordance here hangs off that button.
 *
 * `view` replaced a `showBoxes` boolean in doc 67. The boolean could say "mask" and "mask
 * + box" and never "box alone", so the one view for checking extents against a detector
 * was unreachable. A box with no mask is drawn under every view — there is nothing else of
 * it to draw.
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type JSX,
  type KeyboardEvent,
} from 'react';

import { fitContain, toDisplay, type Rect, type RenderedImage } from '../lib/geometry';
import { useBoxDraw } from '../hooks/useBoxDraw';
import { inPaintOrder, type NumberedBox } from '../lib/boxReview';
import { MaskLayer } from './MaskLayer';
import { showsBoxes, showsMasks, type AnnotationView } from '../types/annotationView';
import { LABEL_TITLES, nextLabel, type CanvasBox, type Label } from '../types/annotation';

export interface AnnotationCanvasProps {
  readonly imageUrl: string;
  readonly naturalWidth: number;
  readonly naturalHeight: number;
  /** Every box, numbered against the *unfiltered* list so a number never moves. */
  readonly boxes: readonly NumberedBox[];
  readonly selectedId: string | null;
  readonly onBoxesChange: (boxes: CanvasBox[]) => void;
  readonly onSelect: (id: string | null) => void;
  /** Ids the threshold is hiding. Hidden boxes are not drawn and cannot be focused, but
   *  they are still in `boxes` and still saved — hiding is a view, not a deletion. */
  readonly hidden?: ReadonlySet<string>;
  /** Draw the rectangle over a segmented annotation as well as its mask (doc 61).
   *  Ignored by anything with no mask — a box with no segmentation is always drawn, or
   *  there would be nothing on screen at all. */
  /** Which half of a segmented annotation to draw (doc 67). */
  readonly view?: AnnotationView;
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

const EMPTY_HIDDEN: ReadonlySet<string> = new Set<string>();

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
  hidden = EMPTY_HIDDEN,
  view = 'both',
  disabled = false,
}: AnnotationCanvasProps): JSX.Element {
  const plain = boxes.map((entry) => entry.box);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [rendered, setRendered] = useState<RenderedImage>(EMPTY_RENDER);

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
      onBoxesChange(plain.map((box) => (box.id === id ? { ...box, label } : box)));
    },
    [plain, onBoxesChange],
  );

  const removeBox = useCallback(
    (id: string): void => {
      onBoxesChange(plain.filter((box) => box.id !== id));
      onSelect(null);
    },
    [plain, onBoxesChange, onSelect],
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

  const addDrawn = useCallback(
    (natural: Rect): void => {
      const created: CanvasBox = {
        id: makeId(),
        label: 'positive',
        provenance: 'hand-drawn',
        x: Math.round(natural.x),
        y: Math.round(natural.y),
        w: Math.round(natural.w),
        h: Math.round(natural.h),
      };
      onBoxesChange([...plain, created]);
      onSelect(created.id);
    },
    [plain, onBoxesChange, onSelect],
  );

  const clearSelection = useCallback((): void => onSelect(null), [onSelect]);

  const draw = useBoxDraw({
    containerRef,
    rendered,
    disabled,
    onDraw: addDrawn,
    onStrayClick: clearSelection,
  });

  return (
    <div className="canvas">
      <div
        ref={containerRef}
        className="canvas__stage"
        data-testid="canvas-stage"
        onPointerDown={draw.onPointerDown}
        onPointerMove={draw.onPointerMove}
        onPointerUp={draw.onPointerUp}
      >
        <img
          className="canvas__image"
          src={imageUrl}
          alt=""
          draggable={false}
          onLoad={measure}
        />

        {showsMasks(view) && (
          <MaskLayer boxes={boxes} hidden={hidden} rendered={rendered} selectedId={selectedId} />
        )}

        {inPaintOrder(boxes)
          .filter(({ box }) => !hidden.has(box.id))
          .map(({ box, number }) => {
            const rect = toDisplay(box, rendered);
            const selected = box.id === selectedId;
            // A segmented annotation's rect is hidden unless asked for, but the button
            // stays: it is the only focusable thing a mask has, and removing it would
            // take the verdict keys and the accessibility tree with it.
            const bare = box.mask !== undefined && !showsBoxes(view);
            const score =
              box.score === undefined ? '' : `, score ${(box.score * 100).toFixed(0)}%`;
            return (
              <button
                key={box.id}
                type="button"
                className={`canvas__box canvas__box--${box.label}${selected ? ' canvas__box--selected' : ''}${bare ? ' canvas__box--bare' : ''}`}
                style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
                aria-pressed={selected}
                aria-label={`Box ${number}${box.text ? `, ${box.text}` : ''}, ${LABEL_TITLES[box.label].toLowerCase()}${score}. Press 1, 2 or 3 to relabel, Delete to remove.`}
                disabled={disabled}
                onClick={() => {
                  onSelect(box.id);
                  setLabel(box.id, nextLabel(box.label));
                }}
                onFocus={() => onSelect(box.id)}
                onKeyDown={(event) => handleBoxKeyDown(event, box)}
              >
                <span className="canvas__boxtag">
                  <span className="canvas__boxnum">{number}</span>
                  {box.text ?? LABEL_TITLES[box.label]}
                </span>
              </button>
            );
          })}

        {draw.draft && (
          <div
            className="canvas__draft"
            style={{
              left: draw.draft.x,
              top: draw.draft.y,
              width: draw.draft.w,
              height: draw.draft.h,
            }}
            aria-hidden="true"
          />
        )}
      </div>

      <p className="canvas__hint">
        Drag on the image to draw a box. Click a box to cycle its label, or use the list
        beside it. With a box focused: <kbd>1</kbd> positive, <kbd>2</kbd> negative,{' '}
        <kbd>3</kbd> unclear, <kbd>Delete</kbd> to remove.
      </p>
    </div>
  );
}
