/**
 * Carry my corrections to the next picture (doc 170).
 *
 * Pure: what the user made of a picture's model proposals (`recordCorrections`), and the
 * same decisions applied to the next picture's proposals (`applyCorrections`). "The same
 * object" is the same model class and a strong overlap, paired one to one, best first.
 */

import type { CanvasBox, Label } from '../types/annotation';
import { iou } from './mergeProposal';
import { phraseKey } from './phraseEdit';

/** Strict on purpose: a missed match costs a click, a wrong one a wrong label. */
export const CARRY_IOU = 0.6;

/** One decision about one model proposal, at the place the model put it. */
export interface Correction {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  /** What the model called it — the key for matching, never the user's rename. */
  readonly modelClass: string;
  readonly removed: boolean;
  readonly label: Label;
  readonly text: string | undefined;
}

export interface CarryCounts {
  readonly renamed: number;
  readonly verdicts: number;
  readonly removed: number;
}

/** What changed between each proposal as the model made it and as the user left it. */
export function recordCorrections(
  originals: ReadonlyMap<string, CanvasBox>,
  final: readonly CanvasBox[],
): Correction[] {
  const byId = new Map(final.map((box) => [box.id, box]));
  const corrections: Correction[] = [];
  for (const [id, model] of originals) {
    const left = byId.get(id);
    const place = { x: model.x, y: model.y, w: model.w, h: model.h, modelClass: model.text ?? '' };
    if (!left) {
      corrections.push({ ...place, removed: true, label: model.label, text: model.text });
    } else if (phraseKey(left.text ?? '') !== phraseKey(model.text ?? '') || left.label !== model.label) {
      corrections.push({ ...place, removed: false, label: left.label, text: left.text });
    }
  }
  return corrections;
}

/** Pairs of (proposal, correction), best overlap first, each side used once. */
function pairs(proposals: readonly CanvasBox[], corrections: readonly Correction[]): Map<number, Correction> {
  const candidates: { p: number; c: number; overlap: number }[] = [];
  proposals.forEach((proposal, p) =>
    corrections.forEach((correction, c) => {
      if (phraseKey(proposal.text ?? '') !== phraseKey(correction.modelClass)) return;
      const overlap = iou(proposal, correction);
      if (overlap >= CARRY_IOU) candidates.push({ p, c, overlap });
    }),
  );
  candidates.sort((a, b) => b.overlap - a.overlap);
  const matched = new Map<number, Correction>();
  const used = new Set<number>();
  for (const { p, c } of candidates) {
    const correction = corrections[c];
    if (matched.has(p) || used.has(c) || !correction) continue;
    matched.set(p, correction);
    used.add(c);
  }
  return matched;
}

/** The proposals with the matching decisions applied; removed ones are left out. */
export function applyCorrections(
  proposals: readonly CanvasBox[],
  corrections: readonly Correction[],
): { readonly boxes: CanvasBox[]; readonly counts: CarryCounts } {
  const matched = pairs(proposals, corrections);
  const boxes: CanvasBox[] = [];
  let renamed = 0;
  let verdicts = 0;
  let removed = 0;
  proposals.forEach((proposal, p) => {
    const correction = matched.get(p);
    if (!correction) return void boxes.push(proposal);
    if (correction.removed) return void (removed += 1);
    if (phraseKey(correction.text ?? '') !== phraseKey(proposal.text ?? '')) renamed += 1;
    if (correction.label !== proposal.label) verdicts += 1;
    const { text: _dropped, ...rest } = proposal;
    boxes.push({ ...rest, label: correction.label, ...(correction.text !== undefined ? { text: correction.text } : {}) });
  });
  return { boxes, counts: { renamed, verdicts, removed } };
}
