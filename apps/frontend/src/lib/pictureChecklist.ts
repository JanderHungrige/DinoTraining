/**
 * What one picture still lacks for the model it is annotated for (doc 104).
 *
 * Pure: the annotations on the canvas, the dataset's phrases and this picture's statuses
 * in, one line per layer out. The Studio marks a required layer that is not met; it never
 * blocks saving, because partial work is normal.
 */

import type { LayerId } from '../api/annotationTargets';
import type { PictureStatus } from '../api/phrases';
import type { Translator } from '../i18n';
import type { CanvasBox } from '../types/annotation';

export interface CheckLine {
  readonly layer: LayerId;
  readonly met: boolean;
  readonly text: string;
}

export function checkLine(
  layer: LayerId,
  boxes: readonly CanvasBox[],
  phraseCount: number,
  statuses: readonly PictureStatus[],
  { t, tp }: Translator,
): CheckLine {
  const positives = boxes.filter((box) => box.label === 'positive');
  const classes = [...new Set(positives.map((box) => (box.text ?? '').trim().toLowerCase()).filter(Boolean))];
  switch (layer) {
    case 'picture-class':
      if (classes.length === 0) return { layer, met: false, text: t('studio.check.nothingYet') };
      return classes.length === 1
        ? { layer, met: true, text: t('studio.check.oneClass', { name: classes[0] ?? '' }) }
        : { layer, met: false, text: t('studio.check.severalClasses', { names: classes.join(', ') }) };
    case 'boxes':
      return positives.length > 0
        ? { layer, met: true, text: tp('studio.check.objects', positives.length) }
        : { layer, met: false, text: t('studio.check.nothingYet') };
    case 'masks': {
      const outlined = positives.filter((box) => box.mask !== undefined).length;
      if (positives.length === 0) return { layer, met: false, text: t('studio.check.nothingYet') };
      return outlined === positives.length
        ? { layer, met: true, text: t('studio.check.allOutlined', { count: positives.length }) }
        : { layer, met: false, text: t('studio.check.someOutlined', { done: outlined, count: positives.length }) };
    }
    case 'phrases': {
      const phrases = new Set(positives.flatMap((box) => box.phrases ?? (box.text ? [box.text.toLowerCase()] : [])));
      return phrases.size > 0
        ? { layer, met: true, text: [...phrases].join(', ') }
        : { layer, met: false, text: t('studio.check.noPhrase') };
    }
    case 'picture-status':
      if (phraseCount === 0) return { layer, met: false, text: t('studio.check.noPhrases') };
      return statuses.length >= phraseCount
        ? { layer, met: true, text: tp('studio.check.checkedAll', phraseCount) }
        : { layer, met: false, text: tp('studio.check.checkedSome', phraseCount, { checked: statuses.length }) };
    default:
      throw new Error(`Unhandled layer: ${layer satisfies never}`);
  }
}
