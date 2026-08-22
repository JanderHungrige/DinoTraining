/**
 * Image with an overlay of reviewable segmentation masks.
 *
 * A **sibling** of `AnnotationCanvas`, not an extension of it. That component owns drawing,
 * dragging and resizing rectangles — none of which applies here, because mask review is
 * verdict-only. Folding masks into it would have added a second geometry model to a file
 * already at the project's size limit, and every future box change would have had to reason
 * about masks it never touches.
 *
 * What the two do share is the part that must not diverge: the same three verdicts, the
 * same click-to-cycle gesture, the same 1/2/3 keys, and real focusable buttons so keyboard
 * operation and the accessibility tree come for free.
 *
 * The **mask's bounding box is the hit target.** Mask pixels are an awkward thing to click
 * and impossible to focus; the box — derived server-side in `27-grounded-sam-annotator`, so
 * nothing here decodes an RLE — gives a control that behaves like the box canvas's.
 */

import { useCallback, useEffect, useRef, useState, type JSX, type KeyboardEvent } from 'react';

import { fitContain, toDisplay, type RenderedImage } from '../lib/geometry';
import type { Rgb } from '../lib/overlayPalette';
import { LABEL_TITLES, LABELS, nextLabel, type Label, type ReviewMask } from '../types/annotation';
import { MapOverlay } from './overlays/MapOverlay';

export interface MaskReviewCanvasProps {
  readonly imageUrl: string;
  readonly naturalWidth: number;
  readonly naturalHeight: number;
  readonly masks: readonly ReviewMask[];
  readonly selectedId: string | null;
  readonly onMasksChange: (masks: ReviewMask[]) => void;
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

/** Verdict colours, matching the box canvas's borders so one legend serves both. */
const VERDICT_RGB: Readonly<Record<Label, Rgb>> = Object.freeze({
  positive: { r: 74, g: 222, b: 128 },
  negative: { r: 248, g: 113, b: 113 },
  unclear: { r: 251, g: 191, b: 36 },
});

/** Background is transparent; only the object is tinted. */
function alphaForBinary(value: number): number {
  return value > 0 ? 255 : 0;
}

export function MaskReviewCanvas({
  imageUrl,
  naturalWidth,
  naturalHeight,
  masks,
  selectedId,
  onMasksChange,
  onSelect,
  disabled = false,
}: MaskReviewCanvasProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [rendered, setRendered] = useState<RenderedImage>(EMPTY_RENDER);

  const measure = useCallback(() => {
    const node = containerRef.current;
    if (!node) return;
    const { width, height } = node.getBoundingClientRect();
    setRendered(fitContain(width, height, naturalWidth, naturalHeight));
  }, [naturalWidth, naturalHeight]);

  // Re-measure on resize: letterboxing changes with the container, and a stale
  // measurement puts every mask's hit target in the wrong place.
  useEffect(() => {
    measure();
    const node = containerRef.current;
    if (!node || typeof ResizeObserver === 'undefined') return;

    const observer = new ResizeObserver(measure);
    observer.observe(node);
    return () => observer.disconnect();
  }, [measure]);

  const setLabel = (id: string, label: Label): void => {
    onMasksChange(masks.map((mask) => (mask.id === id ? { ...mask, label } : mask)));
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>, mask: ReviewMask): void => {
    const index = ['1', '2', '3'].indexOf(event.key);
    if (index >= 0) {
      event.preventDefault();
      const label = LABELS[index];
      if (label) setLabel(mask.id, label);
    }
    // Deliberately no Delete: a rejected mask is `negative`, which is information the
    // trainer can use. Removing it would throw that away silently.
  };

  return (
    <div className="canvas">
      <div className="canvas__stage" ref={containerRef}>
        <img className="canvas__image" src={imageUrl} alt="" onLoad={measure} draggable={false} />

        {masks.map((mask) => (
          <MapOverlay
            key={`${mask.id}-map`}
            encoded={mask.maskPng}
            width={naturalWidth}
            height={naturalHeight}
            rendered={rendered}
            colourFor={() => VERDICT_RGB[mask.label]}
            alphaFor={alphaForBinary}
            opacity={mask.id === selectedId ? 0.75 : 0.45}
            title={`${LABEL_TITLES[mask.label]} mask${mask.concept ? `: ${mask.concept}` : ''}`}
          />
        ))}

        {masks.map((mask) => {
          const rect = toDisplay(mask, rendered);
          const selected = mask.id === selectedId;
          const score = mask.score !== undefined ? `, ${(mask.score * 100).toFixed(0)}%` : '';
          return (
            <button
              key={mask.id}
              type="button"
              className={`canvas__box canvas__box--${mask.label}${
                selected ? ' canvas__box--selected' : ''
              } canvas__box--mask`}
              style={{ left: rect.x, top: rect.y, width: rect.w, height: rect.h }}
              aria-pressed={selected}
              aria-label={`${LABEL_TITLES[mask.label]} mask${
                mask.concept ? `: ${mask.concept}` : ''
              }${score}. Press 1, 2 or 3 to change the verdict.`}
              disabled={disabled}
              onClick={() => {
                onSelect(mask.id);
                setLabel(mask.id, nextLabel(mask.label));
              }}
              onFocus={() => onSelect(mask.id)}
              onKeyDown={(event) => handleKeyDown(event, mask)}
            >
              <span className="canvas__boxtag">
                {LABEL_TITLES[mask.label]}
                {mask.score !== undefined ? ` ${(mask.score * 100).toFixed(0)}%` : ''}
              </span>
            </button>
          );
        })}
      </div>

      <p className="canvas__hint">
        Click a mask to cycle its verdict, or press 1, 2 or 3 with it focused. Rejecting a
        mask keeps it as a negative rather than deleting it — the trainer can use that.
      </p>
    </div>
  );
}
