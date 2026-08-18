/**
 * Head-catalogue slice of the API contract.
 *
 * Mirrors backend/app/api/v1/head_catalog.py. As elsewhere, every response gets a
 * runtime guard so a backend change surfaces at the boundary rather than as
 * `undefined` inside a card.
 */

import { apiFetch } from './client';
import { isHeadInstance, type HeadInstanceInfo } from './headInstances';

export interface CatalogEntry {
  readonly id: string;
  readonly title: string;
  readonly task: string;
  readonly head_type_id: string;
  readonly backbone_id: string;
  readonly trained_on: string;
  readonly licence: string;
  readonly size_bytes: number;
  readonly num_classes: number | null;
  readonly installed: boolean;
  readonly installed_instance_id: string | null;
  readonly backbone_installed: boolean;
  /** Null unless a backbone was supplied — matches GET /head-types. */
  readonly compatible: boolean | null;
  readonly incompatible_reason: string | null;
}

export interface ImportRequest {
  readonly repo_id: string;
  readonly head_type_id: string;
  readonly backbone_id: string;
  readonly num_classes?: number | null;
  readonly name?: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isCatalogEntry(value: unknown): value is CatalogEntry {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['title'] === 'string' &&
    typeof value['task'] === 'string' &&
    typeof value['backbone_id'] === 'string' &&
    typeof value['trained_on'] === 'string' &&
    typeof value['licence'] === 'string' &&
    typeof value['size_bytes'] === 'number' &&
    typeof value['installed'] === 'boolean' &&
    typeof value['backbone_installed'] === 'boolean'
  );
}

function isCatalogList(value: unknown): value is { entries: CatalogEntry[] } {
  return (
    isRecord(value) && Array.isArray(value['entries']) && value['entries'].every(isCatalogEntry)
  );
}

/** Human-readable size. Heads are MB-scale, so one decimal is the useful precision. */
export function formatSize(bytes: number): string {
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export async function listHeadCatalog(
  backbone?: string,
  signal?: AbortSignal,
): Promise<CatalogEntry[]> {
  const query = backbone ? `?backbone=${encodeURIComponent(backbone)}` : '';
  const body = await apiFetch(
    `/head-catalog${query}`,
    isCatalogList,
    signal ? { signal } : undefined,
  );
  return body.entries;
}

export function installCatalogEntry(entryId: string): Promise<HeadInstanceInfo> {
  return apiFetch(`/head-catalog/${encodeURIComponent(entryId)}/install`, isHeadInstance, {
    method: 'POST',
  });
}

export function importCommunityHead(request: ImportRequest): Promise<HeadInstanceInfo> {
  return apiFetch('/heads/import', isHeadInstance, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
}
