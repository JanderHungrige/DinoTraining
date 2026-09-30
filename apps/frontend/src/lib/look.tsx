/**
 * The app's look preferences, shared (doc 77).
 *
 * A context rather than two `usePersistentState` calls on one key: Admin's switch and the
 * background layer are different components, and two hook instances on one key do not see
 * each other's writes — flipping the switch would change storage and nothing on screen.
 */

import { createContext, useContext, type JSX, type ReactNode } from 'react';

import { usePersistentState } from '../hooks/usePersistentState';
import { isBoolean } from './persisted';

export interface Look {
  readonly animatedBackground: boolean;
  readonly setAnimatedBackground: (on: boolean) => void;
}

const LookContext = createContext<Look>({
  animatedBackground: true,
  setAnimatedBackground: () => undefined,
});

export function LookProvider({ children }: { readonly children: ReactNode }): JSX.Element {
  const [animatedBackground, setAnimatedBackground] = usePersistentState(
    'look.animatedBackground',
    true,
    isBoolean,
  );
  return (
    <LookContext.Provider value={{ animatedBackground, setAnimatedBackground }}>
      {children}
    </LookContext.Provider>
  );
}

export function useLook(): Look {
  return useContext(LookContext);
}
