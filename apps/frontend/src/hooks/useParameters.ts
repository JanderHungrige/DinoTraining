/**
 * One model's training parameters (doc 100): the catalogue, loaded, plus the user's own
 * changes, remembered per model family.
 *
 * Only the **overrides** are state. The effective values are derived as defaults ⊕
 * overrides on every render — CLAUDE.md's rule: nothing is seeded from the catalogue,
 * which arrives asynchronously. Before it arrives `values` is empty.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  getParameters,
  problemWith,
  type ParameterSetInfo,
  type ParameterValue,
} from '../api/parameters';
import { useT } from '../i18n';
import { readPersisted, writePersisted, type Guard } from '../lib/persisted';

export type Overrides = Readonly<Record<string, ParameterValue>>;

const isRecord: Guard<Record<string, unknown>> = (value): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

/** The remembered changes, minus anything that is not a usable value. A half-typed number
 *  is stored as NaN, which JSON writes as null; dropping that one entry keeps the rest,
 *  where rejecting the record would forget every change the user made. */
function readOverrides(family: string): Overrides {
  const raw = readPersisted(`params.${family}`, {}, isRecord);
  return Object.fromEntries(
    Object.entries(raw).filter(
      (entry): entry is [string, ParameterValue] =>
        (typeof entry[1] === 'number' && Number.isFinite(entry[1])) ||
        typeof entry[1] === 'boolean' ||
        typeof entry[1] === 'string',
    ),
  );
}

export interface Parameters {
  readonly set: ParameterSetInfo | null;
  readonly error: string;
  /** Every parameter's effective value; empty until the catalogue has loaded. */
  readonly values: Readonly<Record<string, ParameterValue>>;
  readonly overrides: Overrides;
  /** Keys whose value cannot be sent, with the reason. */
  readonly invalid: Readonly<Record<string, string>>;
  readonly change: (key: string, value: ParameterValue) => void;
  readonly reset: (key: string) => void;
  readonly resetAll: () => void;
}

function useCatalogue(modelId: string): { set: ParameterSetInfo | null; error: string } {
  const [loaded, setLoaded] = useState<{ id: string; set: ParameterSetInfo } | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!modelId) return;
    let live = true;
    setError('');
    getParameters(modelId)
      .then((set) => live && setLoaded({ id: modelId, set }))
      .catch((cause: unknown) => live && setError(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [modelId]);
  // A set loaded for the previous model is not this model's.
  return { set: loaded && loaded.id === modelId ? loaded.set : null, error };
}

export function useParameters(modelId: string): Parameters {
  const { set, error } = useCatalogue(modelId);
  const translator = useT();
  const family = set?.family ?? '';
  const [store, setStore] = useState<Record<string, Overrides>>({});
  const overrides: Overrides = useMemo(
    () => (family ? store[family] ?? readOverrides(family) : {}),
    [family, store],
  );

  const write = useCallback(
    (next: Overrides) => {
      if (!family) return;
      writePersisted(`params.${family}`, next);
      setStore((current) => ({ ...current, [family]: next }));
    },
    [family],
  );

  const values = useMemo(() => {
    if (!set) return {};
    const known = Object.fromEntries(set.parameters.map((p) => [p.key, p.default]));
    // An override for a key the catalogue no longer lists is ignored, not sent.
    const kept = Object.entries(overrides).filter(([key]) => key in known);
    return { ...known, ...Object.fromEntries(kept) };
  }, [set, overrides]);

  const invalid = useMemo(() => {
    const found: Record<string, string> = {};
    for (const parameter of set?.parameters ?? []) {
      const value = values[parameter.key];
      const problem = value === undefined ? '' : problemWith(parameter, value, translator);
      if (problem) found[parameter.key] = problem;
    }
    return found;
  }, [set, values, translator]);

  const change = useCallback(
    (key: string, value: ParameterValue) => {
      const fallback = set?.parameters.find((p) => p.key === key)?.default;
      const rest = without(overrides, key);
      write(value === fallback ? rest : { ...rest, [key]: value });
    },
    [set, overrides, write],
  );
  const reset = useCallback(
    (key: string) => write(without(overrides, key)),
    [overrides, write],
  );
  const resetAll = useCallback(() => write({}), [write]);

  return { set, error, values, overrides, invalid, change, reset, resetAll };
}

function without(overrides: Overrides, key: string): Overrides {
  return Object.fromEntries(Object.entries(overrides).filter(([k]) => k !== key));
}

/** A fine-tune request's fields: three named, every other value as an option. */
export function finetuneFields(values: Readonly<Record<string, ParameterValue>>): {
  epochs?: number;
  learning_rate?: number;
  seed?: number;
  options: Record<string, number>;
} {
  const { epochs, learning_rate: rate, seed, ...rest } = values;
  const options: Record<string, number> = {};
  for (const [key, value] of Object.entries(rest)) {
    // The backend's options are numbers; a switch travels as 0 or 1.
    options[key] = Number(value);
  }
  return {
    ...(typeof epochs === 'number' ? { epochs } : {}),
    ...(typeof rate === 'number' ? { learning_rate: rate } : {}),
    ...(typeof seed === 'number' ? { seed } : {}),
    options,
  };
}
