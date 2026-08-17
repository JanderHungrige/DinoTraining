/**
 * Annotation shapes shared by the canvas and the workflow.
 *
 * Mirrors backend/app/datasets/models.py. Coordinates are image-natural pixels,
 * top-left origin — the one convention used from the model output all the way to
 * the COCO export.
 */

export type Label = 'positive' | 'negative' | 'unclear';
export type Provenance = 'grounding-dino' | 'hand-drawn';

export const LABELS: readonly Label[] = Object.freeze(['positive', 'negative', 'unclear']);

export const LABEL_TITLES: Readonly<Record<Label, string>> = Object.freeze({
  positive: 'Positive',
  negative: 'Negative',
  unclear: 'Unclear',
});

/** A box as the canvas holds it. `id` is client-side only. */
export interface CanvasBox {
  readonly id: string;
  readonly label: Label;
  readonly provenance: Provenance;
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly score?: number;
  readonly text?: string;
}

/** Click cycles rather than opening a menu — the same call, hundreds of times. */
export function nextLabel(label: Label): Label {
  const index = LABELS.indexOf(label);
  return LABELS[(index + 1) % LABELS.length] ?? 'positive';
}
