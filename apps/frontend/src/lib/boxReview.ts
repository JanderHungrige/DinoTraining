/**
 * Ordering, numbering and threshold rules for box review (doc 47).
 *
 * Pure, and separate from the canvas, because all three rules are the kind that fail
 * silently: a wrong paint order makes a box unclickable, a wrong numbering makes the side
 * list disagree with the image, and a wrong threshold makes the user's own work vanish.
 * None of them throws.
 */

import type { CanvasBox, Label } from '../types/annotation';

/** A box with the number the reviewer sees. */
export interface NumberedBox {
  readonly box: CanvasBox;
  /** 1-based, and fixed to the box's position in the *unfiltered* list. */
  readonly number: number;
}

/**
 * Number every box by its position in the list as given.
 *
 * Deliberately not by paint order or by score: the number is how a person says "that one"
 * out loud, so it must not move when the threshold slider moves or when a box is relabelled.
 */
export function numbered(boxes: readonly CanvasBox[]): NumberedBox[] {
  return boxes.map((box, index) => ({ box, number: index + 1 }));
}

/**
 * Paint order: **largest first, so the smallest lands on top.**
 *
 * This is the fix for the bug Jan reported — a box covered by a larger one could not be
 * clicked. Every box is an absolutely-positioned button filling its own rect, so a big box
 * painted after a small one swallows every click meant for it. Ordering by descending area
 * means a box that *entirely* contains another can never hide it, because the contained box
 * is by definition smaller and therefore painted later.
 *
 * Partial overlap is still ambiguous where the two actually cross, and no paint order fixes
 * that in general — which is why the side list exists.
 *
 * Ties keep their original relative order, so the list is stable across re-renders.
 */
export function inPaintOrder(boxes: readonly NumberedBox[]): NumberedBox[] {
  return [...boxes].sort((a, b) => area(b.box) - area(a.box));
}

function area(box: CanvasBox): number {
  return Math.max(0, box.w) * Math.max(0, box.h);
}

/**
 * Which boxes the threshold hides.
 *
 * **A box with no score is never hidden.** Hand-drawn boxes carry no score, and so do
 * boxes from an imported dataset — dragging a confidence slider must not make the user's
 * own work disappear. Treating a missing score as 0 would do exactly that, silently, and
 * the box would then be dropped by the very next save.
 */
export function hiddenByThreshold(
  boxes: readonly CanvasBox[],
  threshold: number,
): ReadonlySet<string> {
  const hidden = new Set<string>();
  for (const box of boxes) {
    if (box.score !== undefined && box.score < threshold) hidden.add(box.id);
  }
  return hidden;
}

/** True when any box carries a score — the slider is meaningless otherwise. */
export function hasScores(boxes: readonly CanvasBox[]): boolean {
  return boxes.some((box) => box.score !== undefined);
}

/** The verdict counts the review header reports. */
export function verdictCounts(
  boxes: readonly CanvasBox[],
): Readonly<Record<Label, number>> {
  const counts: Record<Label, number> = { positive: 0, negative: 0, unclear: 0 };
  for (const box of boxes) counts[box.label] += 1;
  return counts;
}
