/** A dataset's annotation guideline and second look (doc 109). Mirrors dataset_quality.py. */

import { apiFetch } from './client';
import { hasFields, jsonBody } from './prepGuards';

export type SecondLookVerdict = 'right' | 'changed';

export interface SecondLookInfo {
  readonly sample: readonly string[];
  readonly verdicts: Readonly<Record<string, SecondLookVerdict>>;
  readonly reviewed: number;
  readonly changed: number;
  /** Share of reviewed pictures that needed a change; null until one is reviewed. */
  readonly rate: number | null;
}

const base = (datasetId: string): string => `/datasets/${encodeURIComponent(datasetId)}`;
const isGuideline = (v: unknown): v is { text: string } => hasFields(v, { text: 'string' });
const isLook = (v: unknown): v is SecondLookInfo =>
  hasFields(v, { sample: 'array', verdicts: 'object', reviewed: 'number', changed: 'number' });

export async function getGuideline(datasetId: string): Promise<string> {
  return (await apiFetch(`${base(datasetId)}/guideline`, isGuideline)).text;
}

export async function saveGuideline(datasetId: string, text: string): Promise<string> {
  const body = await apiFetch(`${base(datasetId)}/guideline`, isGuideline, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  });
  return body.text;
}

export function startSecondLook(datasetId: string, share = 0.05): Promise<SecondLookInfo> {
  return apiFetch(`${base(datasetId)}/second-look`, isLook, jsonBody({ share, seed: Date.now() % 100_000 }));
}

export function getSecondLook(datasetId: string): Promise<SecondLookInfo> {
  return apiFetch(`${base(datasetId)}/second-look`, isLook);
}

export function recordVerdict(datasetId: string, path: string, verdict: SecondLookVerdict): Promise<SecondLookInfo> {
  return apiFetch(`${base(datasetId)}/second-look/verdict`, isLook, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, verdict }),
  });
}
