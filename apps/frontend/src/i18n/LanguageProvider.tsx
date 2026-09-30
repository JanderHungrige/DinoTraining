/**
 * The app's language (doc 111): remembered, defaulting to the OS language, applied to
 * `<html lang>` and sent to the backend with every request.
 */

import { createContext, useEffect, useMemo, type JSX, type ReactNode } from 'react';

import { setApiLanguage } from '../api/client';
import { usePersistentState } from '../hooks/usePersistentState';
import { isOneOf } from '../lib/persisted';
import { ENGLISH, translator, type Translator } from './translate';
import type { Language } from './types';

export interface LanguageState extends Translator {
  readonly setLang: (lang: Language) => void;
}

export const LanguageContext = createContext<LanguageState>({ ...ENGLISH, setLang: () => undefined });

export function systemLanguage(): Language {
  const found = typeof navigator === 'undefined' ? '' : navigator.language ?? '';
  return found.toLowerCase().startsWith('de') ? 'de' : 'en';
}

const isLanguage = isOneOf<Language>(['en', 'de']);

export function LanguageProvider({ children }: { readonly children: ReactNode }): JSX.Element {
  const [lang, setLang] = usePersistentState<Language>('language', systemLanguage(), isLanguage);
  // Before the first render's children fetch anything, so their first request already
  // carries the language.
  setApiLanguage(lang);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const value = useMemo(() => ({ ...translator(lang), setLang }), [lang, setLang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
