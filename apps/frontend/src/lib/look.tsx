/**
 * The app's look preferences, shared (docs 77, 164).
 *
 * A context rather than separate `usePersistentState` calls on one key: the Settings tab's
 * controls and the background layer are different components, and two hook instances on
 * one key do not see each other's writes — flipping a switch would change storage and
 * nothing on screen.
 *
 * The theme is applied as `data-theme="dark|light"` on `<html>`. "System" is resolved
 * here, from the OS setting and its changes, so the stylesheets need only one light block
 * and no media query.
 */

import { createContext, useContext, useEffect, useState, type JSX, type ReactNode } from 'react';

import { usePersistentState } from '../hooks/usePersistentState';
import { isBoolean, isOneOf } from './persisted';

export const THEMES = ['system', 'dark', 'light'] as const;
export type Theme = (typeof THEMES)[number];

export interface Look {
  readonly animatedBackground: boolean;
  readonly setAnimatedBackground: (on: boolean) => void;
  readonly theme: Theme;
  readonly setTheme: (theme: Theme) => void;
  /** What is shown: the theme, with "system" resolved. */
  readonly resolvedTheme: 'dark' | 'light';
}

const LookContext = createContext<Look>({
  animatedBackground: true,
  setAnimatedBackground: () => undefined,
  theme: 'system',
  setTheme: () => undefined,
  resolvedTheme: 'dark',
});

const LIGHT_QUERY = '(prefers-color-scheme: light)';

function systemQuery(): MediaQueryList | null {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' ? window.matchMedia(LIGHT_QUERY) : null;
}

function useSystemPrefersLight(): boolean {
  const [light, setLight] = useState(() => Boolean(systemQuery()?.matches));
  useEffect(() => {
    const query = systemQuery();
    if (!query) return;
    const changed = (): void => setLight(query.matches);
    query.addEventListener('change', changed);
    return () => query.removeEventListener('change', changed);
  }, []);
  return light;
}

export function LookProvider({ children }: { readonly children: ReactNode }): JSX.Element {
  const [animatedBackground, setAnimatedBackground] = usePersistentState(
    'look.animatedBackground',
    true,
    isBoolean,
  );
  const [theme, setTheme] = usePersistentState<Theme>('look.theme', 'system', isOneOf(THEMES));
  const systemLight = useSystemPrefersLight();
  const resolvedTheme = theme === 'system' ? (systemLight ? 'light' : 'dark') : theme;

  useEffect(() => {
    document.documentElement.dataset['theme'] = resolvedTheme;
  }, [resolvedTheme]);

  return (
    <LookContext.Provider value={{ animatedBackground, setAnimatedBackground, theme, setTheme, resolvedTheme }}>
      {children}
    </LookContext.Provider>
  );
}

export function useLook(): Look {
  return useContext(LookContext);
}
