/**
 * Foundation-model slice of the API contract. Mirrors backend/app/api/v1/foundation.py.
 *
 * A foundation model predicts on its own — no backbone, no head, no shared pass. It still
 * returns a `Prediction`, which is what lets the viewer put it in a pane beside a trained
 * head and the overlay registry draw it without knowing the difference.
 */

import { apiFetch } from './client';
import { isPrediction, type Prediction } from './inference';
import type { CanvasBox } from '../types/annotation';

export interface FoundationInfo {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly task: string;
  readonly render_hint: string;
  readonly model_id: string;
  readonly licence: string;
  /** Shown in the viewer as well as the admin panel — this is where the output is used. */
  readonly non_commercial: boolean;
  readonly installed: boolean;
  readonly approx_size_mb: number;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isFoundation(value: unknown): value is FoundationInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['title'] === 'string' &&
    typeof value['installed'] === 'boolean' &&
    typeof value['non_commercial'] === 'boolean'
  );
}

function isFoundationList(value: unknown): value is { foundations: FoundationInfo[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['foundations']) &&
    value['foundations'].every(isFoundation)
  );
}

export async function listFoundations(signal?: AbortSignal): Promise<FoundationInfo[]> {
  const body = await apiFetch(
    '/foundation',
    isFoundationList,
    signal ? { signal } : undefined,
  );
  return body.foundations;
}

export interface RunFoundationOptions {
  readonly imagePath: string;
  readonly foundationId: string;
}

export function runFoundation(
  options: RunFoundationOptions,
  signal?: AbortSignal,
): Promise<Prediction> {
  return apiFetch('/foundation/predict', isPrediction, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      foundation_id: options.foundationId,
    }),
    ...(signal ? { signal } : {}),
  });
}

// --- proposals (doc 42) -------------------------------------------------------------
//
// Deliberately the same shape the expert route returns, because the review surface should
// consume one shape rather than learn which kind of model produced a box.

export interface FoundationProposalResponse {
  readonly image_path: string;
  readonly width: number;
  readonly height: number;
  readonly device: string;
  readonly model_name: string;
  readonly model_summary: string;
  readonly boxes: readonly {
    readonly label: CanvasBox['label'];
    readonly provenance: CanvasBox['provenance'];
    readonly x: number;
    readonly y: number;
    readonly w: number;
    readonly h: number;
    readonly score: number | null;
    readonly prompt: string | null;
    readonly producer: CanvasBox['producer'] | null;
  }[];
}

function isFoundationProposal(value: unknown): value is FoundationProposalResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value['width'] === 'number' &&
    typeof value['height'] === 'number' &&
    typeof value['model_name'] === 'string' &&
    Array.isArray(value['boxes'])
  );
}

export interface ProposeFoundationOptions {
  readonly imagePath: string;
  readonly foundationId: string;
  readonly scoreThreshold?: number;
}

export function proposeWithFoundation(
  options: ProposeFoundationOptions,
  signal?: AbortSignal,
): Promise<FoundationProposalResponse> {
  return apiFetch('/generate/foundation', isFoundationProposal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      foundation_id: options.foundationId,
      ...(options.scoreThreshold !== undefined
        ? { score_threshold: options.scoreThreshold }
        : {}),
    }),
    ...(signal ? { signal } : {}),
  });
}

/** Same mapping the expert route gets: the class rides as `text` and is renamed to
 *  `prompt` on save (doc 31). */
export function foundationCanvasBoxes(
  response: FoundationProposalResponse,
): CanvasBox[] {
  return response.boxes.map((box, index) => ({
    id: `foundation-${index}`,
    label: box.label,
    provenance: box.provenance,
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    ...(box.score !== null ? { score: box.score } : {}),
    ...(box.prompt ? { text: box.prompt } : {}),
    ...(box.producer ? { producer: box.producer } : {}),
  }));
}

// --- fine-tuning (doc 44) ------------------------------------------------------------

export interface FinetuneEpoch {
  readonly epoch: number;
  readonly train_loss: number;
  readonly metrics: Record<string, number>;
}

export interface FinetuneJob {
  readonly job_id: string;
  readonly state: 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';
  readonly epoch: number;
  readonly total_epochs: number;
  readonly best_metric: number | null;
  readonly class_names: readonly string[];
  /** Proof the backbone was actually frozen — a silent no-op looks like a slow success. */
  readonly frozen_parameters: number;
  readonly trainable_parameters: number;
  readonly message: string;
  readonly instance_id: string | null;
  readonly history: readonly FinetuneEpoch[];
}

function isFinetuneJob(value: unknown): value is FinetuneJob {
  if (!isRecord(value)) return false;
  return (
    typeof value['job_id'] === 'string' &&
    typeof value['state'] === 'string' &&
    typeof value['total_epochs'] === 'number' &&
    Array.isArray(value['history'])
  );
}

export interface StartFinetuneOptions {
  readonly foundationId: string;
  readonly datasetIds: readonly string[];
  readonly name: string;
  readonly epochs: number;
  readonly learningRate: number;
}

export function startFinetune(options: StartFinetuneOptions): Promise<FinetuneJob> {
  return apiFetch('/foundation/finetune', isFinetuneJob, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      foundation_id: options.foundationId,
      dataset_ids: options.datasetIds,
      name: options.name,
      epochs: options.epochs,
      learning_rate: options.learningRate,
    }),
  });
}

export function readFinetune(jobId: string, signal?: AbortSignal): Promise<FinetuneJob> {
  return apiFetch(
    `/foundation/finetune/${encodeURIComponent(jobId)}`,
    isFinetuneJob,
    signal ? { signal } : undefined,
  );
}

export function cancelFinetune(jobId: string): Promise<FinetuneJob> {
  return apiFetch(`/foundation/finetune/${encodeURIComponent(jobId)}/cancel`, isFinetuneJob, {
    method: 'POST',
  });
}

