/**
 * What one picture still lacks for the model it is annotated for (doc 104).
 *
 * Pure: the annotations on the canvas, the dataset's phrases and this picture's statuses
 * in, one line per layer out. The Studio marks a required layer that is not met; it never
 * blocks saving, because partial work is normal.
 */

import type { LayerId } from '../api/annotationTargets';
import type { PictureStatus } from '../api/phrases';
import type { CanvasBox } from '../types/annotation';

export interface CheckLine {
  readonly layer: LayerId;
  readonly met: boolean;
  readonly text: string;
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

export function checkLine(
  layer: LayerId,
  boxes: readonly CanvasBox[],
  phraseCount: number,
  statuses: readonly PictureStatus[],
): CheckLine {
  const positives = boxes.filter((box) => box.label === 'positive');
  const classes = [...new Set(positives.map((box) => (box.text ?? '').trim().toLowerCase()).filter(Boolean))];
  switch (layer) {
    case 'picture-class':
      if (classes.length === 0) return { layer, met: false, text: 'Nothing marked yet' };
      return classes.length === 1
        ? { layer, met: true, text: `One class: ${classes[0]}` }
        : { layer, met: false, text: `Several classes (${classes.join(', ')}): a classifier skips this picture` };
    case 'boxes':
      return positives.length > 0
        ? { layer, met: true, text: plural(positives.length, 'object') }
        : { layer, met: false, text: 'Nothing marked yet' };
    case 'masks': {
      const outlined = positives.filter((box) => box.mask !== undefined).length;
      if (positives.length === 0) return { layer, met: false, text: 'Nothing marked yet' };
      return outlined === positives.length
        ? { layer, met: true, text: `All ${positives.length} have an outline` }
        : { layer, met: false, text: `${outlined} of ${positives.length} have an outline` };
    }
    case 'phrases': {
      const phrases = new Set(positives.flatMap((box) => box.phrases ?? (box.text ? [box.text.toLowerCase()] : [])));
      return phrases.size > 0
        ? { layer, met: true, text: [...phrases].join(', ') }
        : { layer, met: false, text: 'No phrase yet' };
    }
    case 'picture-status':
      if (phraseCount === 0) return { layer, met: false, text: 'No phrases in this dataset yet' };
      return statuses.length >= phraseCount
        ? { layer, met: true, text: `Checked for all ${plural(phraseCount, 'phrase')}` }
        : { layer, met: false, text: `Checked for ${statuses.length} of ${plural(phraseCount, 'phrase')}` };
    default:
      throw new Error(`Unhandled layer: ${layer satisfies never}`);
  }
}
