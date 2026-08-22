/**
 * Model-manager slice of the API contract.
 *
 * Mirrors backend/app/api/v1/models.py and system.py. Each response gets a runtime
 * guard so a backend change surfaces here rather than as `undefined` in a card.
 */

import { apiFetch } from './client';
import type { Device } from './types';

// Mirrors `ModelKind` in backend/app/ml/registry.py. It had already drifted before doc 35
// noticed: `segmenter` arrived with Wave 4's SAM entries and was never added here, and
// nothing failed because no TypeScript ever assigned one. Grep this file whenever a
// backend literal changes — see the Wave 4 handoff.
export type ModelKind = 'detector' | 'backbone' | 'segmenter' | 'depth-estimator';
export type ModelFamily =
  | 'grounding-dino'
  | 'dinov2'
  | 'dinov3'
  | 'sam2'
  | 'sam3'
  | 'depth-anything';
export type JobState = 'pending' | 'downloading' | 'complete' | 'failed';

// Record<ModelFamily, string> rather than a partial map: adding a family to the type
// without a label here is a compile error, not a section that quietly fails to render.
export const FAMILY_LABELS: Readonly<Record<ModelFamily, string>> = Object.freeze({
  'grounding-dino': 'Grounding DINO — open-vocabulary detection',
  dinov2: 'DINOv2 — backbones',
  dinov3: 'DINOv3 — backbones (gated)',
  sam2: 'SAM 2.1 — segmentation (open)',
  sam3: 'SAM 3 — segmentation (gated, your own token)',
  'depth-anything': 'Depth Anything V2 — monocular depth',
});

export interface ModelInfo {
  readonly id: string;
  readonly repo_id: string;
  readonly kind: ModelKind;
  readonly family: ModelFamily;
  readonly gated: boolean;
  readonly approx_size_mb: number;
  readonly description: string;
  readonly licence: string;
  readonly licence_url: string;
  /** True when a token alone is not enough and Meta must also grant access. SAM 3 only. */
  readonly requires_access_request: boolean;
  /** True when the licence forbids commercial use. Authoritative — never parsed from `licence`. */
  readonly non_commercial: boolean;
  readonly installed: boolean;
  readonly size_on_disk_mb: number;
  readonly available: boolean;
  readonly unavailable_reason: string | null;
}

export interface DownloadJob {
  readonly job_id: string;
  readonly model_id: string;
  readonly state: JobState;
  readonly downloaded_bytes: number;
  readonly total_bytes: number;
  readonly message: string;
}

export interface SystemInfo {
  readonly device: Device;
  readonly cache_dir: string;
  readonly hf_token_present: boolean;
  readonly free_disk_mb: number;
}

export interface DeleteResult {
  readonly id: string;
  readonly removed: boolean;
  readonly freed_mb: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isModelInfo(value: unknown): value is ModelInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['repo_id'] === 'string' &&
    typeof value['description'] === 'string' &&
    typeof value['installed'] === 'boolean' &&
    typeof value['gated'] === 'boolean' &&
    typeof value['available'] === 'boolean' &&
    typeof value['approx_size_mb'] === 'number' &&
    typeof value['size_on_disk_mb'] === 'number'
  );
}

function isModelList(value: unknown): value is { models: ModelInfo[] } {
  return isRecord(value) && Array.isArray(value['models']) && value['models'].every(isModelInfo);
}

export function isDownloadJob(value: unknown): value is DownloadJob {
  if (!isRecord(value)) return false;
  const states: readonly string[] = ['pending', 'downloading', 'complete', 'failed'];
  return (
    typeof value['job_id'] === 'string' &&
    typeof value['model_id'] === 'string' &&
    typeof value['state'] === 'string' &&
    states.includes(value['state'])
  );
}

function isSystemInfo(value: unknown): value is SystemInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['device'] === 'string' &&
    typeof value['cache_dir'] === 'string' &&
    typeof value['hf_token_present'] === 'boolean' &&
    typeof value['free_disk_mb'] === 'number'
  );
}

function isDeleteResult(value: unknown): value is DeleteResult {
  if (!isRecord(value)) return false;
  return typeof value['id'] === 'string' && typeof value['removed'] === 'boolean';
}

export async function listModels(signal?: AbortSignal): Promise<ModelInfo[]> {
  const body = await apiFetch('/models', isModelList, signal ? { signal } : undefined);
  return body.models;
}

export function getSystemInfo(signal?: AbortSignal): Promise<SystemInfo> {
  return apiFetch('/system/info', isSystemInfo, signal ? { signal } : undefined);
}

export function startDownload(modelId: string): Promise<DownloadJob> {
  return apiFetch(`/models/${encodeURIComponent(modelId)}/download`, isDownloadJob, {
    method: 'POST',
  });
}

export function getDownloadJob(jobId: string, signal?: AbortSignal): Promise<DownloadJob> {
  return apiFetch(
    `/models/jobs/${encodeURIComponent(jobId)}`,
    isDownloadJob,
    signal ? { signal } : undefined,
  );
}

export function deleteModel(modelId: string): Promise<DeleteResult> {
  return apiFetch(`/models/${encodeURIComponent(modelId)}`, isDeleteResult, {
    method: 'DELETE',
  });
}
