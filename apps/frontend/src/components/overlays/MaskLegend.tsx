/**
 * Which classes a segmentation actually found, by name and colour.
 *
 * The backend has reported `present_classes` since Wave 3 and **nothing ever read it** —
 * the field was declared in `api/inference.ts` and consumed nowhere. So a segmentation
 * result was a field of coloured regions with no key: you could see that the model had
 * divided the image into six things, and not what any of them were.
 *
 * That was survivable while a pretrained head had no class names at all. Now that ADE20k's
 * 150 names are carried (`app/ml/heads/labels.py`), leaving the field unread would mean
 * supplying the names and still never showing them.
 *
 * **Only the classes present**, not the whole label set. ADE20k has 150 and a typical frame
 * holds five or six; a full key would bury the answer in 144 lines of things that are not
 * in the picture.
 */

import type { JSX } from 'react';

import { classColour, toCssColour } from '../../lib/overlayPalette';
import type { Prediction } from '../../api/inference';

/** Beyond this the key is taller than the image it explains. */
const MAX_ENTRIES = 8;

export interface MaskLegendProps {
  readonly prediction: Prediction;
}

interface Entry {
  readonly index: number;
  readonly name: string;
}

export function legendEntries(prediction: Prediction, limit = MAX_ENTRIES): readonly Entry[] {
  const present = prediction.payload['present_classes'];
  if (!Array.isArray(present)) return [];

  return (present as number[])
    .filter((index) => Number.isInteger(index) && index >= 0)
    // Background is not a finding. It is the absence of one, it is drawn transparent, and
    // a swatch for it would be an invisible colour beside the word "background".
    .filter((index) => prediction.class_names[index] !== 'background')
    .slice(0, limit)
    .map((index) => ({
      index,
      // The same fallback the rest of the app uses: a head whose names are unknown still
      // renders something rather than an empty row.
      name: prediction.class_names[index] ?? `class ${index}`,
    }));
}

export function MaskLegend({ prediction }: MaskLegendProps): JSX.Element | null {
  const entries = legendEntries(prediction);
  if (entries.length === 0) return null;

  return (
    <ul className="overlay__legend" aria-label={`Classes found by ${prediction.head_name}`}>
      {entries.map((entry) => (
        <li key={entry.index} className="overlay__legenditem">
          {/* The swatch is decorative — the name beside it carries the meaning, so a
              screen reader hearing both would hear the class twice. */}
          <span
            className="overlay__swatch"
            aria-hidden="true"
            style={{ background: toCssColour(classColour(entry.index)) }}
          />
          <span>{entry.name}</span>
        </li>
      ))}
    </ul>
  );
}
