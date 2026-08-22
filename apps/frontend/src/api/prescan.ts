/**
 * Prescan client (doc 53) — find the images worth annotating before annotating any.
 *
 * Polled rather than streamed, like the fine-tune panel: a scan reports once per image, so
 * a dropped update costs at most one image's worth of progress and the next poll corrects it.
 */

import { apiFetch } from './client';

export type PrescanKind = 'prompt' | 'head' | 'foundation';

export interface PrescanHit {
  readonly path: string;
  readonly boxes: number;
  readonly best_score: number;
  readonly labels: readonly string[];
}

export interface PrescanJob {
  readonly job_id: string;
  readonly state: string;
  readonly scanned: number;
  readonly total: number;
  /** Images that would not open — reported so a scan that read almost nothing cannot pass
   *  for a scan that found almost nothing. */
  readonly unreadable: number;
  readonly hits: readonly PrescanHit[];
  readonly message: string;
}

export interface StartPrescanOptions {
  readonly kind: PrescanKind;
  readonly imagePaths: readonly string[];
  readonly labels: readonly string[];
  readonly scoreThreshold: number;
  readonly modelId?: string;
  readonly prompt?: string;
  readonly textThreshold?: number;
  readonly backboneId?: string;
  readonly instanceId?: string;
  readonly foundationId?: string;
  readonly concept?: string;
}

function isPrescanJob(value: unknown): value is PrescanJob {
  if (typeof value !== 'object' || value === null) return false;
  const job = value as Record<string, unknown>;
  return (
    typeof job['job_id'] === 'string' &&
    typeof job['state'] === 'string' &&
    typeof job['scanned'] === 'number' &&
    Array.isArray(job['hits'])
  );
}

export function startPrescan(
  options: StartPrescanOptions,
  signal?: AbortSignal,
): Promise<PrescanJob> {
  return apiFetch('/generate/prescan', isPrescanJob, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      kind: options.kind,
      image_paths: options.imagePaths,
      labels: options.labels,
      score_threshold: options.scoreThreshold,
      ...(options.modelId ? { model_id: options.modelId } : {}),
      ...(options.prompt ? { prompt: options.prompt } : {}),
      ...(options.textThreshold === undefined
        ? {}
        : { text_threshold: options.textThreshold }),
      ...(options.backboneId ? { backbone_id: options.backboneId } : {}),
      ...(options.instanceId ? { instance_id: options.instanceId } : {}),
      ...(options.foundationId ? { foundation_id: options.foundationId } : {}),
      ...(options.concept ? { concept: options.concept } : {}),
    }),
    ...(signal ? { signal } : {}),
  });
}

export function readPrescan(jobId: string, signal?: AbortSignal): Promise<PrescanJob> {
  return apiFetch(
    `/generate/prescan/${encodeURIComponent(jobId)}`,
    isPrescanJob,
    signal ? { signal } : {},
  );
}

export function cancelPrescan(jobId: string, signal?: AbortSignal): Promise<PrescanJob> {
  return apiFetch(`/generate/prescan/${encodeURIComponent(jobId)}/cancel`, isPrescanJob, {
    method: 'POST',
    ...(signal ? { signal } : {}),
  });
}

export function isFinished(job: PrescanJob | null): boolean {
  return job !== null && ['complete', 'failed', 'cancelled'].includes(job.state);
}
