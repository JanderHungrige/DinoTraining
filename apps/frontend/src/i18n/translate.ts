/** Looking a key up, filling `{name}` placeholders, choosing plural forms (doc 111). */

import { de, en, type Key } from './catalogue';
import type { Language, Params } from './types';

const CATALOGUES: Readonly<Record<Language, { readonly [K in Key]: string }>> = { en, de };

function fill(text: string, params?: Params): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (whole, name: string) =>
    name in params ? String(params[name]) : whole,
  );
}

export function translate(lang: Language, key: Key, params?: Params): string {
  return fill(CATALOGUES[lang][key] ?? en[key], params);
}

/** Keys that come in `_one` / `_other` pairs, named without the suffix. */
export type PluralKey = {
  [K in Key]: K extends `${infer Base}_one` ? (`${Base}_other` extends Key ? Base : never) : never;
}[Key];

export function translatePlural(lang: Language, key: PluralKey, count: number, params?: Params): string {
  const form = new Intl.PluralRules(lang).select(count) === 'one' ? 'one' : 'other';
  return translate(lang, `${key}_${form}` as Key, { count, ...params });
}

export interface Translator {
  readonly lang: Language;
  readonly t: (key: Key, params?: Params) => string;
  readonly tp: (key: PluralKey, count: number, params?: Params) => string;
}

export function translator(lang: Language): Translator {
  return {
    lang,
    t: (key, params) => translate(lang, key, params),
    tp: (key, count, params) => translatePlural(lang, key, count, params),
  };
}

/** English, for code outside the React tree and for tests that render bare. */
export const ENGLISH: Translator = translator('en');
