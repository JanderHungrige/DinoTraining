/**
 * What a dataset is annotated for (doc 104). Mirrors backend/app/api/v1/annotation_targets.py.
 */

import { apiFetch } from './client';
import { arrayOf, hasFields } from './prepGuards';

export type LayerLevel = 'required' | 'recommended' | 'optional';
export type LayerId = 'picture-class' | 'boxes' | 'masks' | 'phrases' | 'picture-status';

export interface LayerRule {
  readonly layer: LayerId;
  readonly label: string;
  readonly level: LayerLevel;
  readonly why: string;
}

export interface AnnotationTarget {
  readonly id: string;
  readonly label: string;
  readonly summary: string;
  /** The Prepare data profile it trains, or null for "open". */
  readonly profile: string | null;
  readonly layers: readonly LayerRule[];
}

const isTarget = (v: unknown): v is AnnotationTarget =>
  hasFields(v, { id: 'string', label: 'string', summary: 'string', layers: 'array' });

const isChoice = (v: unknown): v is { target: string } => hasFields(v, { target: 'string' });

export function listAnnotationTargets(): Promise<AnnotationTarget[]> {
  return apiFetch('/annotation-targets', arrayOf(isTarget));
}

export function saveDatasetTarget(datasetId: string, target: string): Promise<{ target: string }> {
  return apiFetch(`/datasets/${encodeURIComponent(datasetId)}/annotation-target`, isChoice, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target }),
  });
}
