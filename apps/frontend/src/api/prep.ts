/**
 * Prepare data, first half: targets, audit, fixes and split (docs 81, 83, 84).
 * Mirrors backend/app/api/v1/prep_audit.py, prep_fixes.py and prep_split.py.
 */

import { ApiError, apiFetch } from './client';
import { arrayOf, datasetPath, hasFields, isRecord, jsonBody } from './prepGuards';

export interface PrepTarget {
  readonly id: string;
  readonly label: string;
  readonly task: string;
  readonly annotation_kind: string;
  readonly input_size: number;
  readonly min_visible_px: number;
}

export type Severity = 'problem' | 'warn' | 'info' | 'ok';

export interface Finding {
  readonly id: string;
  readonly severity: Severity;
  readonly title: string;
  readonly what: string;
  readonly why: string;
  readonly action: string;
  readonly examples: readonly string[];
  readonly metrics: Readonly<Record<string, number | string>>;
}

export interface DatasetAudit {
  readonly dataset_id: string;
  readonly target: string | null;
  readonly created_at: string;
  readonly summary: {
    readonly images: number;
    readonly annotations: number;
    readonly classes: Readonly<Record<string, number>>;
    readonly problems: number;
    readonly warnings: number;
  };
  readonly findings: readonly Finding[];
  readonly copy_groups: readonly (readonly string[])[];
  readonly unreadable: readonly string[];
  readonly excluded: number;
}

export interface AuditJob {
  readonly job_id: string;
  readonly state: string;
  readonly done: number;
  readonly total: number;
  readonly message: string;
  readonly audit: DatasetAudit | null;
}

export interface PrepState {
  readonly excluded: readonly string[];
  readonly class_map: Readonly<Record<string, string | null>>;
}

export type FixAction =
  | 'exclude'
  | 'include'
  | 'exclude-copies'
  | 'exclude-unreadable'
  | 'set-class-map';

export interface SideReport {
  readonly images: number;
  readonly classes: Readonly<Record<string, number>>;
}

export interface SplitReport {
  readonly mode: string;
  readonly seed: number;
  readonly groups: number;
  readonly largest_group: number;
  readonly sides: Readonly<Record<'train' | 'val' | 'test', SideReport>>;
  readonly buffer: number;
  readonly warnings: readonly string[];
}

const isTarget = (v: unknown): v is PrepTarget =>
  hasFields(v, { id: 'string', label: 'string', task: 'string', input_size: 'number' });

export const isFinding = (v: unknown): v is Finding =>
  hasFields(v, {
    id: 'string',
    severity: 'string',
    title: 'string',
    what: 'string',
    why: 'string',
    action: 'string',
    examples: 'array',
    metrics: 'object',
  });

export function isAudit(v: unknown): v is DatasetAudit {
  return (
    hasFields(v, { dataset_id: 'string', created_at: 'string', summary: 'object', findings: 'array' }) &&
    isRecord(v) &&
    Array.isArray(v['findings']) &&
    v['findings'].every(isFinding)
  );
}

const isAuditJob = (v: unknown): v is AuditJob =>
  hasFields(v, { job_id: 'string', state: 'string', done: 'number', total: 'number' }) &&
  isRecord(v) &&
  (v['audit'] === null || v['audit'] === undefined || isAudit(v['audit']));

const isPrepState = (v: unknown): v is PrepState =>
  hasFields(v, { excluded: 'array', class_map: 'object' });

const isFixResponse = (v: unknown): v is { changed: number; state: PrepState } =>
  hasFields(v, { changed: 'number', state: 'object' }) && isRecord(v) && isPrepState(v['state']);

export const isSplitReport = (v: unknown): v is SplitReport =>
  hasFields(v, { mode: 'string', seed: 'number', sides: 'object', buffer: 'number', warnings: 'array' });

export function listTargets(): Promise<PrepTarget[]> {
  return apiFetch('/prep/targets', arrayOf(isTarget));
}

export function startAudit(datasetId: string, target: string): Promise<AuditJob> {
  return apiFetch(datasetPath(datasetId, 'audit'), isAuditJob, jsonBody({ target }));
}

export function getAuditJob(jobId: string): Promise<AuditJob> {
  return apiFetch(`/prep/audits/${encodeURIComponent(jobId)}`, isAuditJob);
}

/** A GET whose 404 means "not made yet": null, not an error. */
async function orNull<T>(load: () => Promise<T>): Promise<T | null> {
  try {
    return await load();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/** The last audit, or null when the dataset has none yet. */
export function getLastAudit(datasetId: string): Promise<DatasetAudit | null> {
  return orNull(() => apiFetch(datasetPath(datasetId, 'audit'), isAudit));
}

export function getPrepState(datasetId: string): Promise<PrepState> {
  return apiFetch(datasetPath(datasetId, 'prep-state'), isPrepState);
}

export function applyFix(
  datasetId: string,
  action: FixAction,
  extra: { paths?: readonly string[]; class_map?: Readonly<Record<string, string | null>> } = {},
): Promise<{ changed: number; state: PrepState }> {
  return apiFetch(datasetPath(datasetId, 'fixes'), isFixResponse, jsonBody({ action, ...extra }));
}

export function makeSplit(
  datasetId: string,
  options: { mode?: 'auto' | 'keep-source'; seed?: number } = {},
): Promise<SplitReport> {
  return apiFetch(datasetPath(datasetId, 'split'), isSplitReport, jsonBody(options));
}

/** The stored split, or null when there is none. */
export function getSplit(datasetId: string): Promise<SplitReport | null> {
  return orNull(() => apiFetch(datasetPath(datasetId, 'split'), isSplitReport));
}
