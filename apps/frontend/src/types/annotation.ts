/**
 * Annotation shapes shared by the canvas and the workflow.
 *
 * Mirrors backend/app/datasets/models.py. Coordinates are image-natural pixels,
 * top-left origin — the one convention used from the model output all the way to
 * the COCO export.
 */

export type Label = 'positive' | 'negative' | 'unclear';
/**
 * Who proposed a box. Mirrors PROVENANCE_VALUES in backend/app/datasets/schema.py, where
 * it also lives in a SQLite CHECK constraint — so a value added there needs a migration
 * *and* an entry here. Wave 4 added the last three.
 */
export type Provenance =
  | 'grounding-dino'
  | 'hand-drawn'
  | 'expert-head'
  | 'sam3'
  | 'grounded-sam';

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

/**
 * A mask as the review surface holds it. `id` is client-side only.
 *
 * Verdict-only by design: the three labels are the same three a box carries, so one
 * dataset format and one set of counters serve both. There is deliberately no geometry
 * to edit — SAM's masks are good enough that a verdict is usually the whole review, and
 * a brush would be a much larger surface for a much smaller gain.
 *
 * `x/y/w/h` is the mask's own bounding box in natural pixels, derived server-side. It is
 * the *hit target*: mask pixels are an awkward thing to click or focus, and the box gives
 * a real focusable control — and therefore keyboard operation — for free.
 */
export interface ReviewMask {
  readonly id: string;
  readonly label: Label;
  readonly provenance: Provenance;
  /** Base64 PNG, no data: prefix. 0 = background, 255 = this object. Preview only. */
  readonly maskPng: string;
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly score?: number;
  /** The phrase that produced it — shown beside each mask during review. */
  readonly concept?: string;
}
