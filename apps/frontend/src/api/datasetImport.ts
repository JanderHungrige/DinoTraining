/** Dataset import and parameters (doc 136). Mirrors backend/app/api/v1/dataset_import.py. */

import { apiFetch } from './client';

export type DetectedKind = 'images' | 'video' | 'coco' | 'yolo' | 'voc' | 'openlabel';

export interface Detection {
  readonly path: string;
  readonly kind: DetectedKind;
  readonly name: string;
  readonly pictures: number;
  readonly videos: number;
  readonly annotation_files: number;
  readonly annotated_pictures: number;
  readonly objects: number;
  readonly classes: readonly string[];
  readonly annotation_types: readonly string[];
  readonly splits: readonly string[];
  readonly convention: string | null;
  readonly notes: readonly DetectionNote[];
  /** How many pictures are in no annotation file (note `uncovered`). */
  readonly uncovered: number;
}

export type DetectionNote = 'uncovered' | 'ambiguous-convention' | 'no-annotations' | 'video-frames';

export interface ImportResult {
  readonly dataset_id: string;
  readonly name: string;
  readonly pictures: number;
  readonly annotated_pictures: number;
  readonly objects: number;
  readonly masks: number;
  readonly classes: readonly string[];
  readonly skipped_pictures: number;
  readonly skipped_objects: number;
}

export interface ImportJob {
  readonly job_id: string;
  readonly path: string;
  readonly state: 'running' | 'complete' | 'failed';
  readonly done: number;
  readonly total: number;
  readonly current: string;
  readonly result: ImportResult | null;
  readonly error: string | null;
}

export interface DatasetProfile {
  readonly dataset_id: string;
  readonly name: string;
  readonly created_at: string;
  readonly description: string | null;
  readonly source: string | null;
  readonly media: 'images' | 'video' | 'mixed' | 'empty';
  readonly pictures: number;
  readonly annotated_pictures: number;
  readonly sequences: number;
  readonly classes: readonly string[];
  readonly annotation_types: readonly string[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isDetection(value: unknown): value is Detection {
  return isRecord(value) && typeof value['kind'] === 'string' && typeof value['pictures'] === 'number';
}

function isImportJob(value: unknown): value is ImportJob {
  return isRecord(value) && typeof value['job_id'] === 'string' && typeof value['state'] === 'string';
}

function isProfileList(value: unknown): value is { profiles: DatasetProfile[] } {
  return isRecord(value) && Array.isArray(value['profiles']);
}

export function detectDataset(path: string): Promise<Detection> {
  return apiFetch('/datasets/import/detect', isDetection, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
}

export interface ImportRequest {
  readonly path: string;
  readonly name: string;
  readonly description: string | null;
  readonly copy_images: boolean;
}

export function startImport(request: ImportRequest): Promise<ImportJob> {
  return apiFetch('/datasets/import', isImportJob, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
}

export function getImportJob(jobId: string, signal?: AbortSignal): Promise<ImportJob> {
  return apiFetch(`/datasets/import/jobs/${encodeURIComponent(jobId)}`, isImportJob, signal ? { signal } : undefined);
}

export async function listProfiles(signal?: AbortSignal): Promise<readonly DatasetProfile[]> {
  const body = await apiFetch('/datasets/profiles', isProfileList, signal ? { signal } : undefined);
  return body.profiles;
}
