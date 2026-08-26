/**
 * Which half of a segmentation result you are looking at (doc 67).
 *
 * **Not a boolean.** The Annotation Studio had one — `showBoxes`, with the mask always
 * drawn — and a boolean can express "mask" and "mask + box" but never "box alone", which
 * is the view someone wants when checking extents against a detector. It was the one state
 * the old control could not reach, and the reason this is a union.
 *
 * This is a *display* choice and only that. What gets **saved** is not a choice at all: a
 * stored mask exports as a box already (`coco.py` derives `bbox` and `area` from the RLE),
 * so storing both would put the same object in the export twice — once in each table.
 * Doc 61 settled that; `describeOutput` below is how the app says so out loud.
 */

export type AnnotationView = 'masks' | 'boxes' | 'both';

export const DEFAULT_VIEW: AnnotationView = 'masks';

/** Does this view draw the mask? */
export function showsMasks(view: AnnotationView): boolean {
  return view !== 'boxes';
}

/** Does this view draw the box? */
export function showsBoxes(view: AnnotationView): boolean {
  return view !== 'masks';
}

/**
 * Which views a result can actually offer.
 *
 * A box-only model has no mask to show, so it gets no toggle rather than a control with
 * two dead options. Keyed on what the result *contains* — never on which model produced
 * it, the rule doc 66 applied to `takes_concept` for the same reason.
 */
export function viewsFor(hasMasks: boolean, hasBoxes: boolean): readonly AnnotationView[] {
  if (hasMasks && hasBoxes) return ['masks', 'boxes', 'both'];
  if (hasMasks) return ['masks'];
  if (hasBoxes) return ['boxes'];
  return [];
}

/**
 * What a model of this kind writes into the dataset, in one sentence.
 *
 * Derived from `render_hint`, never from an id: Grounded SAM, SAM 3 and a fine-tuned
 * RF-DETR share no id pattern, and the next model will share one with nothing. Shown
 * *before* a run starts, which is the only point where it can still change the decision.
 */
export function describeOutput(renderHint: string): string {
  if (renderHint === 'masks') {
    return 'Saves segmentation masks. The COCO export also carries a bounding box derived from each mask, so you get both.';
  }
  if (renderHint === 'boxes') {
    return 'Saves bounding boxes.';
  }
  return '';
}

export const VIEW_LABELS: Readonly<Record<AnnotationView, string>> = Object.freeze({
  masks: 'Segmentation',
  boxes: 'Bounding boxes',
  both: 'Both',
});
