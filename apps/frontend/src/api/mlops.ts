/** MLflow settings and status (doc 123). Mirrors backend/app/api/v1/mlops.py. */

import { apiFetch } from './client';
import { hasFields, jsonBody } from './prepGuards';

export interface MlflowStatus {
  readonly configured: boolean;
  readonly uri: string | null;
  readonly experiment: string;
  readonly register_models: boolean;
  /** Which credentials are set — never their values. */
  readonly auth: 'none' | 'basic' | 'token';
  readonly username: string | null;
}

export interface MlflowSettings {
  readonly uri: string;
  readonly experiment: string;
  readonly register_models: boolean;
  /** Left out: keep what is stored. Empty string: remove it. */
  readonly username?: string;
  readonly password?: string;
  readonly token?: string;
}

const isStatus = (v: unknown): v is MlflowStatus =>
  hasFields(v, { configured: 'boolean', experiment: 'string', register_models: 'boolean', auth: 'string' });

export function getMlflowStatus(): Promise<MlflowStatus> {
  return apiFetch('/mlops/status', isStatus);
}

export function saveMlflowSettings(settings: MlflowSettings): Promise<MlflowStatus> {
  return apiFetch('/mlops/settings', isStatus, { ...jsonBody(settings), method: 'PUT' });
}

export function clearMlflowSettings(): Promise<MlflowStatus> {
  return apiFetch('/mlops/settings', isStatus, { method: 'DELETE' });
}

export function testMlflow(): Promise<{ ok: boolean; message: string }> {
  return apiFetch(
    '/mlops/test',
    (v: unknown): v is { ok: boolean; message: string } => hasFields(v, { ok: 'boolean', message: 'string' }),
    { method: 'POST' },
  );
}

/** Doc 124: sending the models trained before, as a job. */
export interface BackfillJob {
  readonly job_id: string;
  readonly state: 'running' | 'complete' | 'failed';
  readonly total: number;
  readonly sent: number;
  readonly skipped: number;
  readonly failed: number;
  readonly notes: readonly string[];
}

const isBackfill = (v: unknown): v is BackfillJob =>
  hasFields(v, { job_id: 'string', state: 'string', total: 'number', sent: 'number', skipped: 'number' });

export function startBackfill(): Promise<BackfillJob> {
  return apiFetch('/mlops/backfill', isBackfill, { method: 'POST' });
}

export function getBackfill(jobId: string): Promise<BackfillJob> {
  return apiFetch(`/mlops/backfill/${encodeURIComponent(jobId)}`, isBackfill);
}
