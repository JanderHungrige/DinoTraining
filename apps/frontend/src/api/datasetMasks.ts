/**
 * One image's stored masks (doc 61).
 * Mirrors backend/app/api/v1/dataset_image_masks.py.
 *
 * **Per image, not in the dataset listing.** The listing ships every image's boxes inline,
 * which is right for four floats each. An RLE is a run list over the whole frame — roughly
 * 15 KB as JSON for a 2464x1600 mask — and a 392-image dataset would make that listing
 * enormous to answer a question about one picture. The Studio shows one image at a time.
 *
 * Loading is not a nicety here: saving *replaces* an image's whole mask set, so a Studio
 * that opened an already-segmented image without its masks would wipe them on the first
 * save.
 */

import { apiFetch } from './client';
import { isDatasetCounts, type DatasetCounts } from './datasets';
import type { CanvasBox, CanvasMask, Label, Provenance } from '../types/annotation';

export interface StoredMaskDto {
  readonly label: Label;
  readonly provenance: Provenance;
  readonly rle: CanvasMask['rle'];
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly score: number | null;
  readonly prompt: string | null;
  readonly producer: CanvasBox['producer'] | null;
  /** Preview only — base64 PNG, 0 background / 255 object. */
  readonly mask_png: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isImageMasks(value: unknown): value is { path: string; masks: StoredMaskDto[] } {
  return (
    isRecord(value) &&
    typeof value['path'] === 'string' &&
    Array.isArray(value['masks']) &&
    value['masks'].every(
      (entry) =>
        isRecord(entry) && isRecord(entry['rle']) && typeof entry['mask_png'] === 'string',
    )
  );
}

let counter = 0;

/**
 * Stored masks as the review surface holds them.
 *
 * They become `CanvasBox`es — not a separate list — so the numbering, the threshold, the
 * verdict buttons and the class picker all keep working on one array. The mask's derived
 * bounding box is the box, exactly as it is for a fresh proposal, which is what gives a
 * mask a focusable hit target for free.
 */
export function storedMasksToCanvasBoxes(masks: readonly StoredMaskDto[]): CanvasBox[] {
  return masks.map((mask) => ({
    id: `mask-${(counter += 1)}`,
    label: mask.label,
    provenance: mask.provenance,
    x: mask.x,
    y: mask.y,
    w: mask.w,
    h: mask.h,
    ...(mask.score === null ? {} : { score: mask.score }),
    ...(mask.prompt ? { text: mask.prompt } : {}),
    ...(mask.producer ? { producer: mask.producer } : {}),
    mask: { rle: mask.rle, png: mask.mask_png },
  }));
}

export async function listImageMasks(
  datasetId: string,
  path: string,
  signal?: AbortSignal,
): Promise<CanvasBox[]> {
  const body = await apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/images/masks?path=${encodeURIComponent(path)}`,
    isImageMasks,
    signal ? { signal } : undefined,
  );
  return storedMasksToCanvasBoxes(body.masks);
}

/**
 * Replace one image's stored masks with the segmented annotations on the canvas.
 *
 * A different function from `saveImageMasks`, not a variant of it. That one pairs reviewed
 * verdicts to an immutable proposal **by array index**, which is right for the Dataset
 * Generator and unsound here: the Studio's list is edited — boxes drawn, boxes removed,
 * `Remove N below` discarding a filtered subset — and a broken pairing is a silent
 * mislabel rather than a failure.
 *
 * Here every annotation carries its own RLE, so there is nothing to pair.
 *
 * An empty list is a real call, not a skip: the endpoint replaces, so this is how an image
 * whose masks were all rejected gets them cleared.
 */
export function saveImageSegmentations(
  datasetId: string,
  image: { path: string; width: number; height: number },
  boxes: readonly CanvasBox[],
): Promise<DatasetCounts> {
  return apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/images/masks`,
    isDatasetCounts,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        path: image.path,
        width: image.width,
        height: image.height,
        masks: boxes
          .filter((box) => box.mask !== undefined)
          .map((box) => ({
            label: box.label,
            provenance: box.provenance,
            rle: box.mask?.rle,
            // `text` is the canvas's name for a class and the store calls it `prompt` —
            // the same rename `saveImageBoxes` does, at the same kind of boundary. Sending
            // `text` would have pydantic drop it and land `prompt` NULL. See doc 31.
            ...(box.text ? { prompt: box.text } : {}),
            ...(box.score === undefined ? {} : { score: box.score }),
            ...(box.producer ? { producer: box.producer } : {}),
          })),
      }),
    },
  );
}
