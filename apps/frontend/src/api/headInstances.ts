/**
 * Head-instance slice of the API contract — the picker every tab shares.
 *
 * Mirrors backend/app/api/v1/heads.py. `summary` is rendered rather than composed
 * locally: if two tabs build their own description, the same head reads differently in
 * each, and the user cannot tell they are the same thing.
 */

import { apiFetch } from './client';
import type { HeadTask, RenderHint } from './heads';

export type HeadInstanceKind = 'pretrained-default' | 'community' | 'trained-here';

export const KIND_LABELS: Readonly<Record<HeadInstanceKind, string>> = Object.freeze({
  'pretrained-default': 'Default',
  community: 'Community',
  'trained-here': 'Trained here',
});

export interface HeadInstanceInfo {
  readonly id: string;
  readonly name: string;
  /** One-line description. Render this; do not rebuild it. */
  readonly summary: string;
  readonly kind: HeadInstanceKind;
  readonly head_type_id: string;
  readonly task: HeadTask;
  /**
   * What this head's output can be drawn as. Ask this, never `task`, when deciding
   * whether a head can do something — the same rule `components/overlays/` follows.
   */
  readonly render_hint: RenderHint;
  readonly backbone_id: string;
  readonly backbone_family: string;
  readonly embed_dim: number;
  readonly num_classes: number;
  /** Training class order — index N here is index N in the weights. */
  readonly class_names: readonly string[];
  readonly dataset_ids: readonly string[];
  readonly metrics: Readonly<Record<string, number>>;
  readonly primary_metric: string | null;
  readonly primary_metric_value: number | null;
  readonly epochs_trained: number;
  readonly best_epoch: number | null;
  readonly source_repo: string | null;
  readonly created_at: string;
  /** Median width of the images this head trained on, or null when the datasets are gone.
   *  Powers the tiling hint (doc 62) and nothing acts on it. */
  readonly trained_width?: number | null;
}

/**
 * The one-line description of a head, composed identically wherever a head is offered.
 *
 * Doc 12's contract is that a head **reads the same in every tab**, from `summary` as the
 * backend composed it and never from a filename. Wave 5 made that literal: the Inference
 * Viewer's multi-select panel and the single-select picker used by the Studio and the
 * Dataset Generator are different *controls* — comparison genuinely needs many, annotation
 * genuinely needs one — but they must not be different *descriptions*. This string was
 * written out twice, byte for byte, in two components; one edit would have made them
 * disagree with nothing failing.
 */
export function describeHead(head: HeadInstanceInfo): string {
  return `${KIND_LABELS[head.kind]} · ${head.summary}`;
}

export interface DeleteHeadResult {
  readonly id: string;
  readonly removed: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

/** Exported because the head-catalogue endpoints return this same shape. */
export function isHeadInstance(value: unknown): value is HeadInstanceInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['name'] === 'string' &&
    typeof value['summary'] === 'string' &&
    typeof value['kind'] === 'string' &&
    typeof value['task'] === 'string' &&
    typeof value['backbone_id'] === 'string' &&
    typeof value['num_classes'] === 'number' &&
    Array.isArray(value['class_names'])
  );
}

function isHeadList(value: unknown): value is { heads: HeadInstanceInfo[] } {
  return isRecord(value) && Array.isArray(value['heads']) && value['heads'].every(isHeadInstance);
}

function isDeleteResult(value: unknown): value is DeleteHeadResult {
  return (
    isRecord(value) && typeof value['id'] === 'string' && typeof value['removed'] === 'boolean'
  );
}

export interface HeadFilters {
  readonly task?: HeadTask;
  /** Hide heads that cannot run against the selected backbone. */
  readonly backbone?: string;
}

export async function listHeadInstances(
  filters: HeadFilters = {},
  signal?: AbortSignal,
): Promise<HeadInstanceInfo[]> {
  const params = new URLSearchParams();
  if (filters.task) params.set('task', filters.task);
  if (filters.backbone) params.set('backbone', filters.backbone);
  const query = params.toString() ? `?${params.toString()}` : '';
  const body = await apiFetch(`/heads${query}`, isHeadList, signal ? { signal } : undefined);
  return body.heads;
}

export function getHeadInstance(id: string, signal?: AbortSignal): Promise<HeadInstanceInfo> {
  const options = signal ? { signal } : undefined;
  return apiFetch(`/heads/${encodeURIComponent(id)}`, isHeadInstance, options);
}

export function deleteHeadInstance(id: string): Promise<DeleteHeadResult> {
  return apiFetch(`/heads/${encodeURIComponent(id)}`, isDeleteResult, {
    method: 'DELETE',
  });
}

/**
 * Group instances by task, for same-task comparison in the Inference Viewer.
 * Comparison needs no separate mechanism — it is this list, filtered.
 */
export function groupByTask(
  instances: readonly HeadInstanceInfo[],
): Map<HeadTask, HeadInstanceInfo[]> {
  const grouped = new Map<HeadTask, HeadInstanceInfo[]>();
  for (const instance of instances) {
    const existing = grouped.get(instance.task);
    if (existing) existing.push(instance);
    else grouped.set(instance.task, [instance]);
  }
  return grouped;
}
