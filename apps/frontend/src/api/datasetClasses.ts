/**
 * The class-vocabulary slice of the API contract (doc 60).
 * Mirrors backend/app/api/v1/dataset_classes.py.
 *
 * Kept apart from `datasets.ts` for the same reason the backend router is: everything here
 * is about *names*, and nothing here reads or writes an annotation. A class still reaches
 * the store as `boxes.prompt` when a box is saved — that path is untouched, which is what
 * keeps this feature off the save path entirely.
 */

import { apiFetch } from './client';

export interface ClassInfo {
  readonly name: string;
  /** How many annotations currently carry it. 0 means created-but-unused, a real state. */
  readonly boxes: number;
  /** False when it was inferred from a box rather than stored — every class in a
   *  dataset that predates the table looks like this. */
  readonly stored: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isClassList(value: unknown): value is { classes: ClassInfo[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['classes']) &&
    value['classes'].every(
      (entry) =>
        isRecord(entry) &&
        typeof entry['name'] === 'string' &&
        typeof entry['boxes'] === 'number' &&
        typeof entry['stored'] === 'boolean',
    )
  );
}

export async function listDatasetClasses(
  datasetId: string,
  signal?: AbortSignal,
): Promise<readonly ClassInfo[]> {
  const body = await apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/classes`,
    isClassList,
    signal ? { signal } : undefined,
  );
  return body.classes;
}

/**
 * Create a class. Returns the **whole** vocabulary, not the one entry.
 *
 * The caller is a picker that has to show every option anyway, and merging one entry into
 * a list it already holds would be a second place for the ordering and the case rule to
 * live. Idempotent server-side: creating one that exists is a 200, not a conflict.
 */
export async function createDatasetClass(
  datasetId: string,
  name: string,
  signal?: AbortSignal,
): Promise<readonly ClassInfo[]> {
  const body = await apiFetch(`/datasets/${encodeURIComponent(datasetId)}/classes`, isClassList, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
    ...(signal ? { signal } : {}),
  });
  return body.classes;
}

/** Remove a class from the vocabulary. Never touches a box — see the backend route. */
export async function deleteDatasetClass(
  datasetId: string,
  name: string,
  signal?: AbortSignal,
): Promise<readonly ClassInfo[]> {
  const body = await apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/classes/${encodeURIComponent(name)}`,
    isClassList,
    { method: 'DELETE', ...(signal ? { signal } : {}) },
  );
  return body.classes;
}
