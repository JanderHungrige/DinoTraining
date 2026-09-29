/**
 * `useState`, remembered across tab switches and restarts (doc 69).
 *
 * The read is synchronous and happens once, in the lazy initialiser. That is not
 * "seeding state from async props" (CLAUDE.md): nothing arrives later to be missed.
 */

import { useCallback, useState, type Dispatch, type SetStateAction } from 'react';

import { readPersisted, writePersisted, type Guard } from '../lib/persisted';

export function usePersistentState<T>(
  key: string,
  initial: T,
  guard: Guard<T>,
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => readPersisted(key, initial, guard));

  const set = useCallback<Dispatch<SetStateAction<T>>>(
    (next) => {
      setValue((current) => {
        const resolved =
          typeof next === 'function' ? (next as (previous: T) => T)(current) : next;
        writePersisted(key, resolved);
        return resolved;
      });
    },
    [key],
  );

  return [value, set];
}
