/**
 * Head-type slice of the API contract.
 *
 * Mirrors backend/app/api/v1/head_types.py. Nothing here hardcodes a task: metrics,
 * render hints and the best-model criterion all come from the backend registry, so a
 * head type added there shows up in the UI without a frontend change.
 */

import { apiFetch } from './client';

export type HeadTask = 'classification' | 'detection' | 'segmentation' | 'depth';
export type RenderHint = 'labels' | 'boxes' | 'masks' | 'depth-map';

export const TASK_LABELS: Readonly<Record<HeadTask, string>> = Object.freeze({
  classification: 'Classification',
  detection: 'Object detection',
  segmentation: 'Segmentation',
  depth: 'Depth estimation',
});

export interface HeadTypeInfo {
  readonly id: string;
  readonly task: HeadTask;
  readonly title: string;
  readonly description: string;
  /** False means usable for inference but not fine-tunable in this app. */
  readonly trainable: boolean;
  readonly target_format: string | null;
  readonly consumes: string;
  readonly geometry: string;
  readonly metrics: readonly string[];
  readonly primary_metric: string | null;
  readonly primary_metric_mode: string | null;
  readonly render_hint: RenderHint;
  /** Null unless a backbone was supplied to the request. */
  readonly compatible: boolean | null;
  readonly incompatible_reason: string | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isHeadTypeInfo(value: unknown): value is HeadTypeInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['task'] === 'string' &&
    typeof value['title'] === 'string' &&
    typeof value['description'] === 'string' &&
    typeof value['trainable'] === 'boolean' &&
    typeof value['render_hint'] === 'string' &&
    Array.isArray(value['metrics'])
  );
}

function isHeadTypeList(value: unknown): value is { head_types: HeadTypeInfo[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['head_types']) &&
    value['head_types'].every(isHeadTypeInfo)
  );
}

/**
 * List head types. Pass a backbone id to get a compatibility verdict per entry.
 *
 * Throws for an unknown backbone (404) or one that is not installed (409) — those are
 * different problems and the caller should say so.
 */
export async function listHeadTypes(
  backbone?: string,
  signal?: AbortSignal,
): Promise<HeadTypeInfo[]> {
  const query = backbone ? `?backbone=${encodeURIComponent(backbone)}` : '';
  const body = await apiFetch(
    `/head-types${query}`,
    isHeadTypeList,
    signal ? { signal } : undefined,
  );
  return body.head_types;
}

/** Head types this app can fine-tune — the set the trainer should offer. */
export function trainableHeadTypes(headTypes: readonly HeadTypeInfo[]): HeadTypeInfo[] {
  return headTypes.filter((headType) => headType.trainable);
}

/** Group by task, for same-task comparison and for the trainer's task picker. */
export function byTask(headTypes: readonly HeadTypeInfo[]): Map<HeadTask, HeadTypeInfo[]> {
  const grouped = new Map<HeadTask, HeadTypeInfo[]>();
  for (const headType of headTypes) {
    const existing = grouped.get(headType.task);
    if (existing) existing.push(headType);
    else grouped.set(headType.task, [headType]);
  }
  return grouped;
}
