/**
 * Mask-annotator slice of the API contract.
 * Mirrors backend/app/ml/annotators/registry.py and app/api/v1/annotators.py.
 *
 * Ids are constants rather than string literals scattered through components, for the
 * same reason the backend keeps them in a registry: the difference between the two
 * annotators is data, and an `annotatorId === 'sam3'` in a component is a defect.
 */

import { apiFetch } from './client';

export const GROUNDED_SAM = 'grounded-sam';
export const SAM3 = 'sam3';

/** How an annotator wants its text. `phrases` takes several things at once separated by
 *  full stops — Grounding DINO was trained that way; `concept` takes one.
 *
 *  Read from the payload, never derived from the id. Grounded SAM is three catalogue rows
 *  now (doc 27), and an `annotatorId === GROUNDED_SAM` was right for exactly one of them
 *  while quietly mis-wording the other two. */
export type PromptStyle = 'phrases' | 'concept';

export interface RequiredModel {
  readonly id: string;
  readonly name: string;
  readonly installed: boolean;
  readonly gated: boolean;
  readonly approx_size_mb: number;
  readonly licence: string;
  readonly licence_url: string;
}

export interface AnnotatorInfo {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly licence: string;
  readonly licence_url: string;
  readonly gated: boolean;
  /** True when a token is not enough and access must also be granted. SAM 3 only. */
  readonly requires_access_request: boolean;
  readonly prompt_style: PromptStyle;
  readonly approx_size_mb: number;
  /** True only when every required model is installed. */
  readonly ready: boolean;
  readonly missing_model_ids: readonly string[];
  readonly models: readonly RequiredModel[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isAnnotatorList(value: unknown): value is { annotators: readonly AnnotatorInfo[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['annotators']) &&
    value['annotators'].every(
      (entry) =>
        isRecord(entry) && typeof entry['id'] === 'string' && typeof entry['ready'] === 'boolean',
    )
  );
}

export async function listAnnotators(signal?: AbortSignal): Promise<readonly AnnotatorInfo[]> {
  const body = await apiFetch('/annotators', isAnnotatorList, signal ? { signal } : undefined);
  return body.annotators;
}
