/**
 * Runtime shape checks for the Prepare-data slice of the API (docs 81–88).
 *
 * The prep responses are larger than most in this app, and a hand-written guard per type
 * would be a page each. `hasFields` checks every named field's kind in one line; the
 * guards in `prep.ts` and `prepPlan.ts` list the fields their UI actually reads.
 */

export type FieldKind =
  | 'string'
  | 'number'
  | 'boolean'
  | 'array'
  | 'object'
  | 'string?'
  | 'number?'
  | 'object?';

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function matches(value: unknown, kind: FieldKind): boolean {
  const optional = kind.endsWith('?');
  if (optional && (value === null || value === undefined)) return true;
  const base = optional ? kind.slice(0, -1) : kind;
  if (base === 'array') return Array.isArray(value);
  if (base === 'object') return isRecord(value);
  return typeof value === base;
}

export function hasFields(value: unknown, fields: Readonly<Record<string, FieldKind>>): boolean {
  if (!isRecord(value)) return false;
  return Object.entries(fields).every(([key, kind]) => matches(value[key], kind));
}

/** A guard for an array whose every item passes `item`. */
export function arrayOf<T>(item: (value: unknown) => value is T) {
  return (value: unknown): value is T[] => Array.isArray(value) && value.every(item);
}

/** JSON body for a POST. */
export function jsonBody(body: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

export function datasetPath(datasetId: string, rest: string): string {
  return `/datasets/${encodeURIComponent(datasetId)}/${rest}`;
}
