/**
 * Classification results.
 *
 * A whole-image label has no position, so this is a panel rather than an overlay in the
 * geometric sense — it deliberately ignores `rendered`. Showing the top few with their
 * scores rather than just the winner is what makes two classifiers comparable: "cat 0.92"
 * against "cat 0.41" is a different claim, and the winner alone hides it.
 */

import type { JSX } from 'react';

import { classColour, toCssColour } from '../../lib/overlayPalette';
import type { Prediction } from '../../api/inference';

/** Enough to see whether the head was confident or merely least-unsure. */
const TOP_N = 5;

export interface LabelOverlayProps {
  readonly prediction: Prediction;
}

interface Ranked {
  readonly index: number;
  readonly name: string;
  readonly score: number;
}

export function topLabels(prediction: Prediction, count = TOP_N): readonly Ranked[] {
  const raw = prediction.payload['scores'];
  if (!Array.isArray(raw)) return [];

  return (raw as number[])
    .map((score, index) => ({
      index,
      // A pretrained default carries 1000 ImageNet ids with no names attached, and the
      // viewer must render something rather than throwing on an index it cannot name.
      name: prediction.class_names[index] ?? `class ${index}`,
      score,
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, count);
}

export function LabelOverlay({ prediction }: LabelOverlayProps): JSX.Element | null {
  const ranked = topLabels(prediction);
  if (ranked.length === 0) return null;

  return (
    <ol className="overlay__labels">
      {ranked.map((entry) => (
        <li key={entry.index} className="overlay__label">
          <span
            className="overlay__swatch"
            style={{ background: toCssColour(classColour(entry.index)) }}
            aria-hidden="true"
          />
          <span className="overlay__labelname">{entry.name}</span>
          <span className="overlay__labelbar" aria-hidden="true">
            <span style={{ width: `${Math.round(entry.score * 100)}%` }} />
          </span>
          <span className="overlay__labelscore">{entry.score.toFixed(3)}</span>
        </li>
      ))}
    </ol>
  );
}
