/**
 * `useState`, remembered across tab switches and restarts (doc 69).
 *
 * The read is synchronous and happens once, in the lazy initialiser. That is not
 * "seeding state from async props" (CLAUDE.md): nothing arrives later to be missed.
 *
 * The write happens **when the setter is called**, never inside a state updater. React
 * runs a queued updater only when the component renders again, and a component that
 * unmounts in the same event never does. That is exactly what Start does to a setup form:
 * it remembers the new dataset, clears the name, and is gone. Writing in the updater lost
 * both, and the next Start created a second dataset of the same name.
 */

import { useCallback, useRef, useState, type Dispatch, type SetStateAction } from 'react';

import { readPersisted, writePersisted, type Guard } from '../lib/persisted';

export function usePersistentState<T>(
  key: string,
  initial: T,
  guard: Guard<T>,
): [T, Dispatch<SetStateAction<T>>] {
  const [value, setValue] = useState<T>(() => readPersisted(key, initial, guard));
  // The latest value *set*, which may be ahead of the latest value rendered: two updater
  // calls in one event must compose, as they do with plain useState.
  const latest = useRef<T>(value);

  const set = useCallback<Dispatch<SetStateAction<T>>>(
    (next) => {
      const resolved =
        typeof next === 'function' ? (next as (previous: T) => T)(latest.current) : next;
      latest.current = resolved;
      writePersisted(key, resolved);
      setValue(resolved);
    },
    [key],
  );

  return [value, set];
}
