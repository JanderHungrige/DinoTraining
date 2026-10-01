/** A dataset's export target and its export (docs 142, 143). Mirrors dataset_exchange.py. */

import { apiFetch } from './client';

export type TargetKind = 'data' | 'folder';

export interface ExportTarget {
  readonly kind: TargetKind | null;
  readonly folder: string | null;
  readonly include_pictures: boolean;
  /** What "with the data" means here; null where it is not offered (pictures inside the app). */
  readonly data_folder: string | null;
  readonly exported_at: string | null;
  readonly exported_folder: string | null;
  readonly changed: boolean;
}

export interface ExportResult {
  readonly folder: string;
  readonly pictures: number;
  readonly annotated: number;
  readonly objects: number;
  readonly pictures_copied: number;
  readonly written_at: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isTarget(value: unknown): value is ExportTarget {
  return isRecord(value) && 'data_folder' in value && typeof value['changed'] === 'boolean';
}

function isResult(value: unknown): value is ExportResult {
  return isRecord(value) && typeof value['folder'] === 'string' && typeof value['pictures'] === 'number';
}

const base = (datasetId: string): string => `/datasets/${encodeURIComponent(datasetId)}/export`;

export function getExportTarget(datasetId: string, signal?: AbortSignal): Promise<ExportTarget> {
  return apiFetch(`${base(datasetId)}/target`, isTarget, signal ? { signal } : undefined);
}

export function setExportTarget(
  datasetId: string,
  target: { readonly kind: TargetKind; readonly folder: string | null; readonly include_pictures: boolean },
): Promise<ExportTarget> {
  return apiFetch(`${base(datasetId)}/target`, isTarget, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(target),
  });
}

/** To the stored target. */
export function exportDataset(datasetId: string): Promise<ExportResult> {
  return apiFetch(base(datasetId), isResult, { method: 'POST' });
}
