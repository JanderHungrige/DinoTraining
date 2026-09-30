/**
 * A proposer's new result merged with what is on the canvas (doc 119): add, never replace
 * what is saved.
 *
 * Kept: saved annotations and hand-drawn ones. Replaced: the previous unsaved proposals.
 * Added: the new proposals — only of class `only` when given (the review for one class) —
 * minus any that overlap a kept annotation of the same class, which would be the one
 * object twice (doc 107's "duplicated").
 */

import type { CanvasBox } from '../types/annotation';
import { phraseKey } from './phraseEdit';

export const SAME_OBJECT_IOU = 0.5;

function iou(a: CanvasBox, b: CanvasBox): number {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  if (w <= 0 || h <= 0) return 0;
  const inter = w * h;
  return inter / (a.w * a.h + b.w * b.h - inter);
}

export function mergeProposal(
  current: readonly CanvasBox[],
  proposed: readonly CanvasBox[],
  only?: string,
): CanvasBox[] {
  const kept = current.filter((box) => box.saved === true || box.provenance === 'hand-drawn');
  const wanted = only === undefined ? proposed : proposed.filter((box) => phraseKey(box.text ?? '') === phraseKey(only));
  const fresh = wanted.filter(
    (box) =>
      !kept.some((old) => phraseKey(old.text ?? '') === phraseKey(box.text ?? '') && iou(old, box) >= SAME_OBJECT_IOU),
  );
  return [...fresh, ...kept];
}
