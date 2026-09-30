/** Shared i18n types (doc 111). */

export type Language = 'en' | 'de';

export const LANGUAGES: readonly { readonly id: Language; readonly name: string }[] = [
  // Each in its own language: someone who cannot read the current one still finds theirs.
  { id: 'en', name: 'English' },
  { id: 'de', name: 'Deutsch' },
];

/** A German catalogue for an English one: exactly its keys, each a string. */
export type Catalogue<T extends Readonly<Record<string, string>>> = { readonly [K in keyof T]: string };

export type Params = Readonly<Record<string, string | number>>;
