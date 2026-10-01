/** Automatic exports (doc 144). Mirrors backend/app/api/v1/exports.py. */

import { apiFetch } from './client';

export interface ExportSettings {
  readonly on_close: boolean;
  /** 0: off. */
  readonly every_minutes: number;
  /** Doc 145: trained models exported here when their training finishes; null: off. */
  readonly model_folder?: string | null;
}

export interface NamedDataset {
  readonly dataset_id: string;
  readonly name: string;
}

export interface AutoReport {
  readonly started_at: string;
  readonly finished_at: string | null;
  readonly reason: 'close' | 'interval' | 'manual';
  readonly exported: readonly NamedDataset[];
  readonly unchanged: number;
  readonly failed: readonly (NamedDataset & { readonly error: string })[];
  readonly unfinished: readonly NamedDataset[];
  readonly no_target: readonly NamedDataset[];
}

export interface ExportStatus {
  readonly running: boolean;
  readonly last: AutoReport | null;
}

export interface RunResponse {
  readonly outcome: 'done' | 'started' | 'busy' | 'off';
  readonly report: AutoReport | null;
}

/** Fired after the settings change, so the interval (useAutoExport) re-reads them. */
export const SETTINGS_EVENT = 'dinotraining:export-settings';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

const isSettings = (value: unknown): value is ExportSettings =>
  isRecord(value) && typeof value['on_close'] === 'boolean' && typeof value['every_minutes'] === 'number';
const isStatus = (value: unknown): value is ExportStatus => isRecord(value) && typeof value['running'] === 'boolean';
const isRun = (value: unknown): value is RunResponse => isRecord(value) && typeof value['outcome'] === 'string';

export function getExportSettings(signal?: AbortSignal): Promise<ExportSettings> {
  return apiFetch('/exports/settings', isSettings, signal ? { signal } : undefined);
}

export function putExportSettings(settings: ExportSettings): Promise<ExportSettings> {
  return apiFetch('/exports/settings', isSettings, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
}

export function getExportStatus(signal?: AbortSignal): Promise<ExportStatus> {
  return apiFetch('/exports/status', isStatus, signal ? { signal } : undefined);
}

export function runExports(reason: 'interval' | 'manual', wait: boolean): Promise<RunResponse> {
  return apiFetch('/exports/run', isRun, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason, wait }),
  });
}

/** Doc 146: what uninstalling now would lose. */
export interface ExportOverview {
  readonly datasets: number;
  readonly no_target: readonly string[];
  readonly unexported: readonly string[];
  readonly models: number;
  readonly model_folder: string | null;
}

const isOverview = (value: unknown): value is ExportOverview =>
  isRecord(value) && typeof value['datasets'] === 'number' && Array.isArray(value['no_target']);

export function getExportOverview(signal?: AbortSignal): Promise<ExportOverview> {
  return apiFetch('/exports/overview', isOverview, signal ? { signal } : undefined);
}
