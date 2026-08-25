/**
 * Writing a Studio image's annotations back (doc 61).
 *
 * Extracted from `useAnnotationSession`, which was at 281 lines against the project's
 * 300-line gate, and the seam is real: everything here answers "which table does this
 * annotation belong in and what does that request look like", and everything there is
 * about navigation and dirty state.
 *
 * **One annotation per object.** An annotation with a mask is a `masks` row; one without
 * is a `boxes` row. Never both for the same object — `build_coco` walks the two tables
 * independently and emits each as its own annotation, and a stored mask already exports
 * with `segmentation`, a `bbox` derived from the RLE, and `area`. Writing a box row too
 * would put two annotations on one object in every export and silently double every
 * segmented object in anything trained from it.
 *
 * **Both sets go out on every save, including empty ones.** Each endpoint *replaces* the
 * image's set, so an empty list is how "none any more" is said — an image whose masks were
 * all rejected must have them cleared, not left behind.
 */

import { saveImageBoxes, type DatasetCounts } from '../api/datasets';
import { saveImageSegmentations } from '../api/datasetMasks';
import type { CanvasBox } from '../types/annotation';

export interface ImageFacts {
  readonly path: string;
  readonly width: number;
  readonly height: number;
  /** The session's phrase, for a prompt run. Null for every other source — see doc 31. */
  readonly prompt: string | null;
}

/** Split by what decides the destination table. */
export function partitionByMask(boxes: readonly CanvasBox[]): {
  readonly segmented: readonly CanvasBox[];
  readonly plain: readonly CanvasBox[];
} {
  return {
    segmented: boxes.filter((box) => box.mask !== undefined),
    plain: boxes.filter((box) => box.mask === undefined),
  };
}

/**
 * Save one image's annotations. Returns the backend's own counters.
 *
 * **Masks first, then boxes.** The two requests are not atomic — there is no endpoint that
 * takes both — so one of them has to go first, and it should be the one whose failure
 * leaves the *least* surprising state. A failed mask write leaves the previous masks and
 * the previous boxes, which is simply "the save did not happen". A failed box write after
 * a successful mask write leaves new masks beside old boxes, which is worse; putting masks
 * first makes that the rarer ordering rather than the guaranteed one.
 *
 * The counters returned are the second call's, which is the backend's aggregate after both
 * writes — never a local tally, which drifts the first time a save fails.
 */
export async function saveAnnotations(
  datasetId: string,
  image: ImageFacts,
  boxes: readonly CanvasBox[],
): Promise<DatasetCounts> {
  const { segmented, plain } = partitionByMask(boxes);

  await saveImageSegmentations(datasetId, image, segmented);
  return saveImageBoxes(
    datasetId,
    { path: image.path, width: image.width, height: image.height, prompt: image.prompt },
    plain,
  );
}
