/**
 * Backbone slice of the API contract.
 *
 * Mirrors backend/app/api/v1/backbones.py. `capabilities` is the descriptor head
 * compatibility is checked against — it is null until the backbone is installed,
 * because it is read from the model's own config on disk.
 */

import { apiFetch } from './client';
import type { ModelFamily } from './models';

export interface BackboneCapabilities {
  readonly patch_size: number;
  /** Head input width — the main compatibility axis. */
  readonly embed_dim: number;
  /** 1 (CLS) + register tokens. DINOv3 has registers; DINOv2 does not. */
  readonly num_prefix_tokens: number;
  readonly num_layers: number;
  readonly image_size: number;
}

export interface BackboneInfo {
  readonly id: string;
  readonly family: ModelFamily;
  readonly gated: boolean;
  readonly installed: boolean;
  readonly capabilities: BackboneCapabilities | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isCapabilities(value: unknown): value is BackboneCapabilities {
  if (!isRecord(value)) return false;
  return (
    typeof value['patch_size'] === 'number' &&
    typeof value['embed_dim'] === 'number' &&
    typeof value['num_prefix_tokens'] === 'number' &&
    typeof value['num_layers'] === 'number' &&
    typeof value['image_size'] === 'number'
  );
}

function isBackboneInfo(value: unknown): value is BackboneInfo {
  if (!isRecord(value)) return false;
  const capabilities = value['capabilities'];
  // null is a valid, expected state — not installed yet. Anything else must be a
  // full descriptor; a partial one would silently break a compatibility check.
  if (capabilities !== null && !isCapabilities(capabilities)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['family'] === 'string' &&
    typeof value['gated'] === 'boolean' &&
    typeof value['installed'] === 'boolean'
  );
}

function isBackboneList(value: unknown): value is { backbones: BackboneInfo[] } {
  return (
    isRecord(value) && Array.isArray(value['backbones']) && value['backbones'].every(isBackboneInfo)
  );
}

export async function listBackbones(signal?: AbortSignal): Promise<BackboneInfo[]> {
  const body = await apiFetch('/backbones', isBackboneList, signal ? { signal } : undefined);
  return body.backbones;
}

/** Installed backbones only — the set a head can actually be trained against. */
export function installedBackbones(backbones: readonly BackboneInfo[]): BackboneInfo[] {
  return backbones.filter((backbone) => backbone.installed);
}
