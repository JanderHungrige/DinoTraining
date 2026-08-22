/** Dataset slice of the API contract. Mirrors backend/app/api/v1/datasets.py. */

import { apiFetch } from './client';
import type { MaskProposalResponse } from './generate';
import type { CanvasBox, ReviewMask } from '../types/annotation';

export interface DatasetCounts {
  readonly images: number;
  readonly boxes: number;
  /**
   * Separate from `boxes`, never summed with it: the trainer consumes the two for
   * different tasks, so a combined "annotations" figure would mean nothing to either.
   * The verdict counters below span both.
   */
  readonly masks: number;
  readonly positive: number;
  readonly negative: number;
  readonly unclear: number;
}

export interface DatasetInfo {
  readonly id: string;
  readonly name: string;
  readonly created_at: string;
  readonly prompt: string | null;
  readonly copy_images: boolean;
  readonly counts: DatasetCounts;
}

export const EMPTY_COUNTS: DatasetCounts = Object.freeze({
  images: 0,
  boxes: 0,
  masks: 0,
  positive: 0,
  negative: 0,
  unclear: 0,
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function isDatasetCounts(value: unknown): value is DatasetCounts {
  if (!isRecord(value)) return false;
  return (['images', 'boxes', 'positive', 'negative', 'unclear'] as const).every(
    (key) => typeof value[key] === 'number',
  );
}

function isDatasetInfo(value: unknown): value is DatasetInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['name'] === 'string' &&
    isDatasetCounts(value['counts'])
  );
}

function isDatasetList(value: unknown): value is { datasets: DatasetInfo[] } {
  return (
    isRecord(value) && Array.isArray(value['datasets']) && value['datasets'].every(isDatasetInfo)
  );
}

export async function listDatasets(signal?: AbortSignal): Promise<DatasetInfo[]> {
  const body = await apiFetch('/datasets', isDatasetList, signal ? { signal } : undefined);
  return body.datasets;
}

export function createDataset(
  name: string,
  prompt: string | null,
  copyImages = false,
): Promise<DatasetInfo> {
  return apiFetch('/datasets', isDatasetInfo, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, prompt, copy_images: copyImages }),
  });
}

/**
 * Save one image's boxes. Replaces any previous set — see 03-dataset-store.
 * Returns the backend's fresh counts, which is what the counter renders.
 */
export function saveImageBoxes(
  datasetId: string,
  image: { path: string; width: number; height: number; prompt?: string | null },
  boxes: readonly CanvasBox[],
): Promise<DatasetCounts> {
  return apiFetch(`/datasets/${encodeURIComponent(datasetId)}/images`, isDatasetCounts, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      path: image.path,
      width: image.width,
      height: image.height,
      prompt: image.prompt ?? null,
      // Strip the client-side id; the backend neither wants nor stores it. `text` is
      // the canvas's name for a box's class, and the store calls it `prompt` — rename it
      // here, at the one boundary where a CanvasBox becomes an API box.
      //
      // Sending `text` unchanged is silently lossy: pydantic drops the unknown field and
      // `prompt` lands NULL. Wave 1 never noticed because the Studio also sends an
      // image-level `prompt` that the backend falls back to; the Dataset Generator has
      // no such prompt — it ran a head, not a phrase — so every generated box lost its
      // class. The trainer derives classes from `prompt`, so re-training on a generated
      // dataset collapsed every box into the single fallback class. See 31.
      boxes: boxes.map(({ id: _id, text, ...box }) => ({
        ...box,
        ...(text ? { prompt: text } : {}),
      })),
    }),
  });
}

export function exportCoco(datasetId: string): Promise<{ path: string; annotations: number }> {
  return apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/export/coco`,
    (value): value is { path: string; annotations: number } =>
      isRecord(value) && typeof value['path'] === 'string',
    { method: 'POST' },
  );
}

/**
 * Save reviewed masks for one image.
 *
 * Takes the original proposal response *and* the reviewed masks, pairing them by index.
 * That is what keeps the RLE out of the review type: the canvas only ever handles the
 * PNG preview and a verdict, while the payload that gets stored is rebuilt here from the
 * response the server sent. The two lists are the same length and the same order by
 * construction — `toReviewMasks` maps one to one.
 */
export function saveImageMasks(
  datasetId: string,
  proposal: MaskProposalResponse,
  reviewed: readonly ReviewMask[],
): Promise<DatasetCounts> {
  if (reviewed.length !== proposal.masks.length) {
    // Not recoverable by guessing: pairing a verdict to the wrong mask is a silent
    // mislabel, which is worse than refusing to save.
    return Promise.reject(
      new Error(
        `Cannot save: ${reviewed.length} reviewed masks against ${proposal.masks.length} proposed.`,
      ),
    );
  }

  return apiFetch(`/datasets/${encodeURIComponent(datasetId)}/images/masks`, isDatasetCounts, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      path: proposal.image_path,
      width: proposal.width,
      height: proposal.height,
      masks: proposal.masks.map((mask, index) => ({
        // The verdict is the reviewer's; everything else is the server's own proposal,
        // returned unchanged so nothing is re-derived on the way back.
        label: reviewed[index]?.label ?? mask.label,
        provenance: mask.provenance,
        rle: mask.rle,
        prompt: mask.concept,
        score: mask.score,
        producer: mask.producer,
      })),
    }),
  });
}
