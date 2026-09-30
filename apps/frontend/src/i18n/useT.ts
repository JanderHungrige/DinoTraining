/** The translator for the current language (doc 111); English outside a provider. */

import { useContext } from 'react';

import { LanguageContext, type LanguageState } from './LanguageProvider';

export function useT(): LanguageState {
  return useContext(LanguageContext);
}
