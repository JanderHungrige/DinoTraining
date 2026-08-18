/**
 * Training slice of the API contract, including the live SSE stream.
 *
 * Mirrors backend/app/api/v1/training.py. `metrics` is an open record on purpose: keys
 * come from whatever the head type declared, so a chart must iterate the keys it
 * receives. Hardcoding 'accuracy' here would silently empty the charts the day a head
 * type reporting mIoU is selected.
 */

import { apiFetch, apiUrl } from './client';

export interface EpochInfo {
  readonly epoch: number;
  readonly train_loss: number;
  readonly val_loss: number;
  readonly metrics: Readonly<Record<string, number>>;
}

export type TrainingState = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';

export const TERMINAL_STATES: readonly TrainingState[] = Object.freeze([
  'complete',
  'failed',
  'cancelled',
]);

export interface JobInfo {
  readonly job_id: string;
  readonly state: TrainingState;
  readonly epoch: number;
  readonly total_epochs: number;
  readonly head_type_id: string;
  readonly backbone_id: string;
  readonly dataset_ids: readonly string[];
  readonly class_names: readonly string[];
  /** Images skipped because their boxes named more than one class. */
  readonly skipped_mixed_class_images: number;
  readonly best_metric: number | null;
  readonly best_epoch: number | null;
  /** Which metric key drives best-model selection — highlight this series. */
  readonly primary_metric: string | null;
  readonly message: string;
  readonly head_instance_id: string | null;
  readonly history: readonly EpochInfo[];
}

export interface TrainingRequest {
  readonly head_type_id: string;
  readonly backbone_id: string;
  readonly dataset_ids: readonly string[];
  readonly epochs?: number;
  readonly batch_size?: number;
  readonly learning_rate?: number;
  readonly weight_decay?: number;
  readonly val_fraction?: number;
  readonly test_fraction?: number;
  readonly split_seed?: number;
  readonly save_best_only?: boolean;
  readonly early_stopping_patience?: number;
  readonly augment?: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export function isJobInfo(value: unknown): value is JobInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['job_id'] === 'string' &&
    typeof value['state'] === 'string' &&
    typeof value['epoch'] === 'number' &&
    typeof value['total_epochs'] === 'number' &&
    Array.isArray(value['history'])
  );
}

function isJobList(value: unknown): value is { jobs: JobInfo[] } {
  return isRecord(value) && Array.isArray(value['jobs']) && value['jobs'].every(isJobInfo);
}

function isCancelResult(value: unknown): value is { job_id: string; cancelled: boolean } {
  return isRecord(value) && typeof value['cancelled'] === 'boolean';
}

export function startTraining(request: TrainingRequest): Promise<JobInfo> {
  return apiFetch('/training/jobs', isJobInfo, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
}

export async function listTrainingJobs(signal?: AbortSignal): Promise<JobInfo[]> {
  const body = await apiFetch('/training/jobs', isJobList, signal ? { signal } : undefined);
  return body.jobs;
}

export function getTrainingJob(jobId: string, signal?: AbortSignal): Promise<JobInfo> {
  const options = signal ? { signal } : undefined;
  return apiFetch(`/training/jobs/${encodeURIComponent(jobId)}`, isJobInfo, options);
}

export function cancelTrainingJob(jobId: string): Promise<{ cancelled: boolean }> {
  return apiFetch(`/training/jobs/${encodeURIComponent(jobId)}/cancel`, isCancelResult, {
    method: 'POST',
  });
}

export interface TrainingStreamHandlers {
  readonly onStatus?: (job: JobInfo) => void;
  readonly onEpoch?: (epoch: EpochInfo) => void;
  readonly onDone?: (job: JobInfo) => void;
  readonly onError?: (error: Error) => void;
}

/**
 * Subscribe to a job's live metrics. Returns an unsubscribe function.
 *
 * EventSource reconnects on its own, which is why the backend re-sends a full `status`
 * snapshot on connect — a reconnecting client must not have to reconstruct the run from
 * events it may have missed.
 */
export function streamTrainingJob(
  jobId: string,
  handlers: TrainingStreamHandlers,
): () => void {
  const source = new EventSource(apiUrl(`/training/jobs/${encodeURIComponent(jobId)}/events`));

  const parse = (raw: string): unknown => {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  };

  source.addEventListener('status', (event) => {
    const data = parse((event as MessageEvent<string>).data);
    if (isJobInfo(data)) handlers.onStatus?.(data);
  });

  source.addEventListener('epoch', (event) => {
    const data = parse((event as MessageEvent<string>).data);
    if (isRecord(data) && typeof data['epoch'] === 'number') {
      handlers.onEpoch?.(data as unknown as EpochInfo);
    }
  });

  source.addEventListener('done', (event) => {
    const data = parse((event as MessageEvent<string>).data);
    if (isJobInfo(data)) handlers.onDone?.(data);
    // The server closes after `done`; without this the browser would reconnect to a
    // finished job forever.
    source.close();
  });

  source.onerror = () => {
    // EventSource fires this on transient drops too, so the run is not assumed dead —
    // only a closed stream is terminal.
    if (source.readyState === EventSource.CLOSED) {
      handlers.onError?.(new Error('Training stream closed'));
    }
  };

  return () => source.close();
}

/** Metric keys present across a run, in first-seen order. Charts iterate this. */
export function metricKeys(history: readonly EpochInfo[]): string[] {
  const keys: string[] = [];
  for (const entry of history) {
    for (const key of Object.keys(entry.metrics)) {
      if (!keys.includes(key)) keys.push(key);
    }
  }
  return keys;
}
