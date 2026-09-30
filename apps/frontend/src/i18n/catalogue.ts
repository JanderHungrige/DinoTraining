/**
 * Every namespace, merged (doc 111). A namespace is added here once — `en/<ns>.ts` and
 * `de/<ns>.ts` — and the German one is type-checked against the English one.
 */

import { commonDe } from './de/common';
import { commonEn } from './en/common';

export const en = {
  ...commonEn,
} as const;

export type Key = keyof typeof en;

export const de: { readonly [K in Key]: string } = {
  ...commonDe,
};
