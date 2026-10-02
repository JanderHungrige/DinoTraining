/** Cloud storage connections (doc 147). Mirrors backend/app/api/v1/cloud.py. Secrets go in, never out. */

import { apiFetch } from './client';
import type { Detection, ImportJob } from './datasetImport';

export type CloudKind = 's3' | 'azure' | 'gcs';

export interface CloudFields {
  readonly name: string;
  readonly kind: CloudKind;
  readonly endpoint: string | null;
  readonly region: string | null;
  readonly account: string | null;
}

export interface CloudConnection extends CloudFields {
  readonly id: string;
  readonly created_at: string;
  /** Which secret parts are set; never their values. */
  readonly secrets_set: readonly string[];
}

export interface CloudTestResult {
  readonly ok: boolean;
  readonly message: string;
}

/** The secret parts each kind holds (backend SECRETS). */
export const SECRET_PARTS: Readonly<Record<CloudKind, readonly string[]>> = {
  s3: ['access_key', 'secret_key'],
  azure: ['account_key', 'sas_token'],
  gcs: ['service_account'],
};

const isRecord = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null;
const isConnection = (value: unknown): value is CloudConnection => isRecord(value) && typeof value['id'] === 'string';
const isList = (value: unknown): value is CloudConnection[] => Array.isArray(value) && value.every(isConnection);
const isResult = (value: unknown): value is CloudTestResult => isRecord(value) && typeof value['ok'] === 'boolean';
const isDeleted = (value: unknown): value is { deleted: true } => isRecord(value) && value['deleted'] === true;

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

export function listConnections(signal?: AbortSignal): Promise<CloudConnection[]> {
  return apiFetch('/cloud/connections', isList, signal ? { signal } : undefined);
}

export function saveConnection(
  fields: CloudFields,
  secrets: Readonly<Record<string, string>>,
  id: string | null,
): Promise<CloudConnection> {
  const body = { ...fields, secrets };
  return id
    ? apiFetch(`/cloud/connections/${encodeURIComponent(id)}`, isConnection, json('PUT', body))
    : apiFetch('/cloud/connections', isConnection, json('POST', body));
}

export async function deleteConnection(id: string): Promise<void> {
  await apiFetch(`/cloud/connections/${encodeURIComponent(id)}`, isDeleted, { method: 'DELETE' });
}

export function testConnection(id: string, bucket: string): Promise<CloudTestResult> {
  return apiFetch(`/cloud/connections/${encodeURIComponent(id)}/test`, isResult, json('POST', { bucket }));
}

/** Doc 148: a bucket's dataset, detected from its listing and annotation files. */
export interface LinkDetection {
  readonly link_id: string;
  readonly detection: Detection;
}

const isLinkDetection = (value: unknown): value is LinkDetection =>
  isRecord(value) && typeof value['link_id'] === 'string' && isRecord(value['detection']);
const isJob = (value: unknown): value is ImportJob => isRecord(value) && typeof value['job_id'] === 'string';

export function detectLink(connectionId: string, bucket: string, prefix: string): Promise<LinkDetection> {
  return apiFetch('/cloud/links/detect', isLinkDetection, json('POST', { connection_id: connectionId, bucket, prefix }));
}

export function startLink(linkId: string, name: string, description: string | null): Promise<ImportJob> {
  return apiFetch('/cloud/links', isJob, json('POST', { link_id: linkId, name, description }));
}

/** Doc 149: the linked pictures' cache. */
export interface CacheState {
  readonly bound_gb: number;
  readonly used_bytes: number;
  readonly datasets: readonly { readonly dataset_id: string; readonly uri: string; readonly pictures: number; readonly cached: number }[];
}

const isCache = (value: unknown): value is CacheState => isRecord(value) && typeof value['bound_gb'] === 'number';

export function getCache(signal?: AbortSignal): Promise<CacheState> {
  return apiFetch('/cloud/cache', isCache, signal ? { signal } : undefined);
}

export function setCacheBound(boundGb: number): Promise<CacheState> {
  return apiFetch('/cloud/cache', isCache, json('PUT', { bound_gb: boundGb }));
}

export function clearCache(): Promise<CacheState> {
  return apiFetch('/cloud/cache/clear', isCache, { method: 'POST' });
}
