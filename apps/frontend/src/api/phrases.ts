/**
 * SAM 3 phrases and per-picture phrase statuses (doc 103). Mirrors
 * backend/app/api/v1/dataset_phrases.py.
 */

import { apiFetch } from './client';
import { arrayOf, hasFields, jsonBody } from './prepGuards';

export type PhraseStatus = 'complete' | 'absent';

export interface PhraseInfo {
  /** Null for a class's implicit phrase that has no row yet. */
  readonly id: number | null;
  readonly text: string;
  readonly class_name: string;
  readonly variants: readonly string[];
  readonly confusable: readonly string[];
  readonly instances: number;
  readonly complete: number;
  readonly absent: number;
  /** Doc 115: the classes it answers for — its one class, or an umbrella's members. */
  readonly classes: readonly string[];
  /** An umbrella term ("screw" over m8 and m9); `class_name` is then ''. */
  readonly umbrella: boolean;
}

export interface PictureStatus {
  readonly phrase_id: number;
  readonly text: string;
  readonly status: PhraseStatus;
}

const isPhrase = (v: unknown): v is PhraseInfo =>
  hasFields(v, {
    text: 'string',
    class_name: 'string',
    variants: 'array',
    instances: 'number',
    classes: 'array',
    umbrella: 'boolean',
  });
const isStatus = (v: unknown): v is PictureStatus =>
  hasFields(v, { phrase_id: 'number', text: 'string', status: 'string' });

const base = (datasetId: string): string => `/datasets/${encodeURIComponent(datasetId)}`;

export function listPhrases(datasetId: string): Promise<PhraseInfo[]> {
  return apiFetch(`${base(datasetId)}/phrases`, arrayOf(isPhrase));
}

/** Comma-separated text: "red car, crimson car" is one phrase with a variation. */
export function addPhrase(datasetId: string, text: string, className?: string): Promise<PhraseInfo> {
  return apiFetch(`${base(datasetId)}/phrases`, isPhrase, jsonBody({ text, class_name: className ?? null }));
}

/** Doc 115: an umbrella term over two or more classes ("screw" for m8 and m9). */
export function addUmbrella(datasetId: string, text: string, classes: readonly string[]): Promise<PhraseInfo> {
  return apiFetch(`${base(datasetId)}/phrases`, isPhrase, jsonBody({ text, classes }));
}

export function changePhrase(
  datasetId: string,
  phraseId: number,
  change: {
    readonly variants?: readonly string[];
    readonly confusable?: readonly string[];
    readonly classes?: readonly string[];
  },
): Promise<PhraseInfo> {
  return apiFetch(`${base(datasetId)}/phrases/${phraseId}`, isPhrase, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(change),
  });
}

/** Deletes a stored phrase with its links and checks; the outlines keep their class. */
export function deletePhrase(datasetId: string, phraseId: number): Promise<{ removed: boolean }> {
  return apiFetch(
    `${base(datasetId)}/phrases/${phraseId}`,
    (v: unknown): v is { removed: boolean } => hasFields(v, { removed: 'boolean' }),
    { method: 'DELETE' },
  );
}

export function pictureStatuses(datasetId: string, path: string): Promise<PictureStatus[]> {
  return apiFetch(`${base(datasetId)}/images/phrase-status?path=${encodeURIComponent(path)}`, arrayOf(isStatus));
}

export function setPictureStatus(
  datasetId: string,
  path: string,
  phrase: string,
  status: PhraseStatus | null,
): Promise<PictureStatus[]> {
  return apiFetch(`${base(datasetId)}/images/phrase-status`, arrayOf(isStatus), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, phrase, status }),
  });
}

/** "This phrase is fully annotated": every unchecked picture becomes complete (it has an
 *  outline of the phrase) or absent (it has none). Checks already set stay (doc 108). */
export function markTheRest(datasetId: string, phrase: string): Promise<{ complete: number; absent: number }> {
  return apiFetch(
    `${base(datasetId)}/phrase-status/fill`,
    (v: unknown): v is { complete: number; absent: number } => hasFields(v, { complete: 'number', absent: 'number' }),
    jsonBody({ phrase }),
  );
}

/** Doc 117: per class, since when it exists and how many saved pictures are unknown for it. */
export interface ClassCompleteness {
  readonly since: string;
  readonly unknown: number;
}

const isCompleteness = (v: unknown): v is Record<string, ClassCompleteness> =>
  typeof v === 'object' && v !== null && Object.values(v).every((c) => hasFields(c, { since: 'string', unknown: 'number' }));

export function getCompleteness(datasetId: string): Promise<Record<string, ClassCompleteness>> {
  return apiFetch(`${base(datasetId)}/completeness`, isCompleteness);
}

/** The saved pictures never looked at for one class, by path (doc 119's review list). */
export function unknownPictures(datasetId: string, className: string): Promise<string[]> {
  return apiFetch(
    `${base(datasetId)}/completeness/unknown?class_name=${encodeURIComponent(className)}`,
    (v: unknown): v is string[] => Array.isArray(v) && v.every((p) => typeof p === 'string'),
  );
}

/** Doc 118, "it does not occur there": the unknown pictures become `absent` for the class. */
export function markAbsentInOlder(datasetId: string, className: string): Promise<{ marked: number }> {
  return apiFetch(
    `${base(datasetId)}/completeness/absent`,
    (v: unknown): v is { marked: number } => hasFields(v, { marked: 'number' }),
    jsonBody({ class_name: className }),
  );
}
