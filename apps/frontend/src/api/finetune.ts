/**
 * Fine-tuning foundation models (docs 92, 93). Mirrors backend/app/api/v1/
 * finetune_requirements.py and finetune_jobs.py.
 */

import { apiFetch } from './client';
import { arrayOf, hasFields, jsonBody } from './prepGuards';

export interface FinetuneRequirements {
  readonly id: string;
  readonly model_id: string;
  readonly label: string;
  readonly task: string;
  readonly annotation_kind: string;
  readonly prompt_kind: string;
  readonly min_images: number;
  readonly min_instances_per_class: number;
  readonly minimums_why: string;
  readonly image_sizes: string;
  readonly recipe_required: boolean;
  readonly gates: readonly string[];
  readonly data_format: string;
  readonly what_trains: string;
  readonly available: boolean;
  readonly unavailable_reason: string;
}

export interface ReadinessCheck {
  readonly id: string;
  readonly title: string;
  readonly passed: boolean;
  readonly detail: string;
  readonly fix: string;
}

export interface Readiness {
  readonly finetune_id: string;
  readonly dataset_id: string;
  readonly recipe_id: string | null;
  readonly ready: boolean;
  readonly checks: readonly ReadinessCheck[];
}

export interface FinetuneEpoch {
  readonly epoch: number;
  readonly train_loss: number;
  readonly metrics: Readonly<Record<string, number>>;
}

export interface FinetuneJobInfo {
  readonly job_id: string;
  readonly finetune_id: string;
  readonly state: string;
  readonly epoch: number;
  readonly total_epochs: number;
  readonly primary_metric: string;
  readonly best_metric: number | null;
  readonly best_epoch: number;
  readonly baseline_metrics: Readonly<Record<string, number>>;
  readonly final_metrics: Readonly<Record<string, number>>;
  readonly held_out: string;
  readonly history: readonly FinetuneEpoch[];
  readonly notes: readonly string[];
  readonly message: string;
  readonly instance_id: string | null;
}

export interface StartFinetune {
  readonly finetune_id: string;
  readonly dataset_ids: readonly string[];
  readonly name: string;
  readonly recipe_id?: string;
  /** Omitted → the model's own default (doc 99). */
  readonly epochs?: number;
  readonly learning_rate?: number;
  readonly seed?: number;
  /** Every other catalogue parameter (doc 99); unknown keys are refused with a 422. */
  readonly options?: Readonly<Record<string, number>>;
}

const isRequirements = (v: unknown): v is FinetuneRequirements =>
  hasFields(v, { id: 'string', label: 'string', data_format: 'string', available: 'boolean', gates: 'array' });

const isReadiness = (v: unknown): v is Readiness => hasFields(v, { ready: 'boolean', checks: 'array' });

export const isFinetuneJob = (v: unknown): v is FinetuneJobInfo =>
  hasFields(v, { job_id: 'string', state: 'string', epoch: 'number', history: 'array', notes: 'array' });

export function listRequirements(): Promise<FinetuneRequirements[]> {
  return apiFetch('/finetune/requirements', arrayOf(isRequirements));
}

export function checkReadiness(finetuneId: string, datasetId: string, recipeId?: string): Promise<Readiness> {
  return apiFetch(
    '/finetune/check',
    isReadiness,
    jsonBody({ finetune_id: finetuneId, dataset_id: datasetId, recipe_id: recipeId ?? null }),
  );
}

export function startFinetune(request: StartFinetune): Promise<FinetuneJobInfo> {
  return apiFetch('/finetune/jobs', isFinetuneJob, jsonBody(request));
}

export function getFinetuneJob(jobId: string): Promise<FinetuneJobInfo> {
  return apiFetch(`/finetune/jobs/${encodeURIComponent(jobId)}`, isFinetuneJob);
}

export function cancelFinetune(jobId: string): Promise<{ cancelled: boolean }> {
  return apiFetch(
    `/finetune/jobs/${encodeURIComponent(jobId)}/cancel`,
    (v: unknown): v is { cancelled: boolean } => hasFields(v, { cancelled: 'boolean' }),
    { method: 'POST' },
  );
}
