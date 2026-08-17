/** Dataset slice of the API contract. Mirrors backend/app/api/v1/datasets.py. */

import { apiFetch } from './client';
import type { CanvasBox } from '../types/annotation';

export interface DatasetCounts {
  readonly images: number;
  readonly boxes: number;
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
      // Strip the client-side id; the backend neither wants nor stores it.
      boxes: boxes.map(({ id: _id, ...box }) => box),
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
