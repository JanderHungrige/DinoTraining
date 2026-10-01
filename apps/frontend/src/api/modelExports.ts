/**
 * Export bundles and model locations (doc 121). Mirrors backend/app/api/v1/model_exports.py.
 */

import { ApiError, apiFetch, apiUrl } from './client';
import { hasFields, jsonBody } from './prepGuards';

export type ExportKind = 'heads' | 'finetuned';

/** Desktop: write `<name>.zip` into `destination`; resolves to the zip's path. */
export function exportModelTo(kind: ExportKind, instanceId: string, destination: string): Promise<{ path: string; file: string }> {
  return apiFetch(
    '/exports',
    (v: unknown): v is { path: string; file: string } => hasFields(v, { path: 'string', file: 'string' }),
    jsonBody({ kind, instance_id: instanceId, destination }),
  );
}

/** Browser: the zip itself, with the name the backend chose. */
export async function downloadModelExport(kind: ExportKind, instanceId: string): Promise<{ name: string; blob: Blob }> {
  const response = await fetch(apiUrl('/exports'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ kind, instance_id: instanceId }),
  });
  if (!response.ok) throw new ApiError(response.status, 'export_failed', `${response.status} ${response.statusText}`);
  const disposition = response.headers.get('content-disposition') ?? '';
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? 'model.zip';
  return { name, blob: await response.blob() };
}

export function modelLocation(kind: ExportKind, instanceId: string): Promise<{ folder: string }> {
  return apiFetch(
    `/exports/${kind}/${encodeURIComponent(instanceId)}/location`,
    (v: unknown): v is { folder: string } => hasFields(v, { folder: 'string' }),
  );
}
