/**
 * Detection boxes, as DOM elements over the image.
 *
 * DOM rather than canvas, matching `05-annotation-canvas`: at the tens of boxes this app
 * produces there is no performance reason for canvas, and each box being a real element
 * means it is in the accessibility tree and can carry a title.
 *
 * Boxes arrive in **source-image pixels** (doc 16 inverts the geometry server-side), so
 * the only conversion here is source → displayed, through `toDisplay` — the one function
 * that owns that conversion.
 */

import type { JSX } from 'react';

import { toDisplay, type RenderedImage } from '../../lib/geometry';
import { classColour, toCssColour } from '../../lib/overlayPalette';
import type { BoxTuple, Prediction } from '../../api/inference';

export interface BoxOverlayProps {
  readonly prediction: Prediction;
  readonly rendered: RenderedImage;
}

function boxesOf(prediction: Prediction): readonly BoxTuple[] {
  const raw = prediction.payload['boxes'];
  return Array.isArray(raw) ? (raw as BoxTuple[]) : [];
}

function numbersOf(prediction: Prediction, key: string): readonly number[] {
  const raw = prediction.payload[key];
  return Array.isArray(raw) ? (raw as number[]) : [];
}

export function BoxOverlay({ prediction, rendered }: BoxOverlayProps): JSX.Element | null {
  const boxes = boxesOf(prediction);
  if (boxes.length === 0) return null;

  const scores = numbersOf(prediction, 'scores');
  const classes = numbersOf(prediction, 'classes');

  return (
    <div className="overlay__boxes">
      {boxes.map((box, index) => {
        const [x, y, w, h] = box;
        const display = toDisplay({ x, y, w, h }, rendered);
        // Read positionally — the backend drops from all three arrays together precisely
        // so index N means the same detection in each.
        const classIndex = classes[index] ?? 0;
        const score = scores[index];
        const name = prediction.class_names[classIndex] ?? `class ${classIndex}`;
        const colour = toCssColour(classColour(classIndex));

        return (
          <div
            key={`${prediction.instance_id}-${index}`}
            className="overlay__box"
            style={{
              // toDisplay already folds in the letterbox offset — adding it again here
              // is the classic double-offset bug.
              left: `${display.x}px`,
              top: `${display.y}px`,
              width: `${display.w}px`,
              height: `${display.h}px`,
              borderColor: colour,
            }}
            title={score === undefined ? name : `${name} (${score.toFixed(2)})`}
          >
            <span className="overlay__boxtag" style={{ background: colour }}>
              {name}
              {score === undefined ? '' : ` ${score.toFixed(2)}`}
            </span>
          </div>
        );
      })}
    </div>
  );
}
