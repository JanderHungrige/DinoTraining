/**
 * Entries that outlive the tab they were typed in (doc 69).
 *
 * `App` renders only the active tab, so leaving one unmounts it and every `useState` in it
 * is gone. `localStorage` covers a tab switch and an app restart with one mechanism.
 *
 * Every stored value is **untrusted on read**: it can come from an older build, be edited by
 * hand, or be cut short. So every read goes through a guard, and anything that fails the
 * guard falls back to the default whole. Half a remembered form looks complete and is not.
 *
 * Storage failing is never the user's problem. A private window, a full quota or disabled
 * storage all throw, and in every one of those cases the form must still work as it did
 * before this module existed.
 */

import type { ImageSource } from '../components/ImageSourceField';
import type { AnnotationView } from '../types/annotationView';

/** Bumped when a stored shape changes incompatibly; old keys are then simply not read. */
const NAMESPACE = 'dinotraining.v1.';

export type Guard<T> = (value: unknown) => value is T;

export function storageKeyFor(key: string): string {
  return `${NAMESPACE}${key}`;
}

export function readPersisted<T>(key: string, fallback: T, guard: Guard<T>): T {
  try {
    const raw = localStorage.getItem(storageKeyFor(key));
    if (raw === null) return fallback;
    const parsed: unknown = JSON.parse(raw);
    return guard(parsed) ? parsed : fallback;
  } catch (error) {
    // A SyntaxError is a corrupted value and deserves no noise; anything else is the
    // storage itself refusing, which is worth one line when someone asks why a form forgot.
    if (!(error instanceof SyntaxError)) {
      console.warn(`Could not read remembered entry "${key}"`, error);
    }
    return fallback;
  }
}

export function writePersisted(key: string, value: unknown): void {
  try {
    localStorage.setItem(storageKeyFor(key), JSON.stringify(value));
  } catch (error) {
    console.warn(`Could not remember entry "${key}"`, error);
  }
}

// --- guards -------------------------------------------------------------------------

export const isString: Guard<string> = (value): value is string => typeof value === 'string';

/** Finite only: JSON writes NaN and Infinity as null, so they could never round-trip. */
export const isNumber: Guard<number> = (value): value is number =>
  typeof value === 'number' && Number.isFinite(value);

export const isBoolean: Guard<boolean> = (value): value is boolean =>
  typeof value === 'boolean';

export function isOneOf<T extends string>(options: readonly T[]): Guard<T> {
  return (value): value is T =>
    typeof value === 'string' && (options as readonly string[]).includes(value);
}

/** For a value that may be absent, such as "no path chosen yet". */
export function isNullable<T>(guard: Guard<T>): Guard<T | null> {
  return (value): value is T | null => value === null || guard(value);
}

export const isAnnotationView: Guard<AnnotationView> = isOneOf<AnnotationView>([
  'masks',
  'boxes',
  'both',
]);

export const isStringArray: Guard<string[]> = (value): value is string[] =>
  Array.isArray(value) && value.every((item) => typeof item === 'string');

export const isImageSource: Guard<ImageSource> = (value): value is ImageSource => {
  if (typeof value !== 'object' || value === null) return false;
  const record = value as Record<string, unknown>;
  if (record.kind === 'folder') return typeof record.folder === 'string';
  if (record.kind === 'dataset') return typeof record.datasetId === 'string';
  if (record.kind === 'video') {
    const range = record.range as Record<string, unknown> | null | undefined;
    return (
      typeof record.path === 'string' &&
      typeof range === 'object' &&
      range !== null &&
      [range.start, range.count, range.stride].every(
        (value) => typeof value === 'number' && Number.isFinite(value),
      )
    );
  }
  return false;
};

/**
 * For shaped records such as a training selection: every key the defaults have must be
 * present with the same `typeof`, and an array must still be an array. Extra keys are
 * tolerated, because a newer build may have added one; a missing one is not.
 */
export function isShapeOf<T extends object>(defaults: T): Guard<T> {
  return (value): value is T => {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    const record = value as Record<string, unknown>;
    return Object.entries(defaults).every(([key, expected]) => {
      const actual = record[key];
      if (Array.isArray(expected)) return Array.isArray(actual);
      return typeof actual === typeof expected && !Array.isArray(actual);
    });
  };
}

/**
 * A remembered id is an *override*, and it may name something deleted since. Returns the
 * id only while it is still offered, so the caller's `|| ids[0]` fallback takes over. An
 * empty list — still loading — offers nothing, which is exactly today's behaviour before
 * the fetch resolves.
 */
export function stillListed(id: string, ids: readonly string[]): string {
  return id !== '' && ids.includes(id) ? id : '';
}
