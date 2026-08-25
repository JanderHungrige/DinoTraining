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
  | 'grounded-sam'
  // A dataset this project did not produce, imported wholesale. See `31-external-dataset-import`.
  | 'imported'
  // A self-contained foundation model — the *kind*, not the model. `producer` names which
  // one, exactly as it does for `expert-head`. See `42-foundation-boxes-everywhere`.
  | 'foundation-model';

export const LABELS: readonly Label[] = Object.freeze(['positive', 'negative', 'unclear']);

export const LABEL_TITLES: Readonly<Record<Label, string>> = Object.freeze({
  positive: 'Positive',
  negative: 'Negative',
  unclear: 'Unclear',
});

/**
 * What produced an annotation, captured when it was proposed.
 *
 * A snapshot rather than a reference: the head may be deleted and the provenance has to
 * outlive it. Carried through review untouched and saved back exactly as received —
 * nothing in the UI composes or edits one.
 */
export interface Producer {
  readonly id: string;
  readonly label: string;
  readonly concept?: string;
}

/**
 * A segmentation as the review surface holds it (doc 61).
 *
 * The RLE travels **on the annotation** rather than being paired to a proposal by index.
 * `saveImageMasks` pairs by index and that is right for the Dataset Generator, whose
 * proposal is immutable and whose review is verdicts-only. The Studio's list is edited —
 * boxes are drawn, removed, and discarded wholesale by the threshold slider — and any of
 * those breaks index pairing. A broken pairing is a *silent* mislabel: the save succeeds
 * and every mask after the edit carries the wrong verdict and class.
 */
export interface CanvasMask {
  /** COCO uncompressed RLE. `size` is [height, width] — COCO's order, not this file's. */
  readonly rle: { readonly size: readonly [number, number]; readonly counts: readonly number[] };
  /** Base64 PNG, no data: prefix. 0 = background, 255 = this object. Preview only. */
  readonly png: string;
}

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
  readonly producer?: Producer;
  /**
   * The segmentation this annotation came from, when it has one (doc 61).
   *
   * Present on a concept segmenter's proposals and on anything loaded back from the
   * `masks` table; absent on a hand-drawn box, a detector's box, and a prompt run. Whether
   * it is present decides which table the annotation is saved to — one object is a mask
   * row **or** a box row, never both, because the COCO exporter emits each table
   * separately and storing both would double every segmented object in the export.
   */
  readonly mask?: CanvasMask;
}

/** Does this annotation carry a segmentation? The one test that decides how it is saved. */
export function isSegmented(box: CanvasBox): boolean {
  return box.mask !== undefined;
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
  readonly producer?: Producer;
}
