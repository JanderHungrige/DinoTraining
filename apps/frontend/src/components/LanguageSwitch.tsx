/** The language switch in the header (doc 111). */

import type { JSX } from 'react';

import { LANGUAGES, useT, type Language } from '../i18n';

export function LanguageSwitch(): JSX.Element {
  const { t, lang, setLang } = useT();
  return (
    <label className="langswitch">
      <span className="visually-hidden">{t('common.language')}</span>
      <select value={lang} aria-label={t('common.language')} onChange={(event) => setLang(event.target.value as Language)}>
        {LANGUAGES.map((entry) => (
          <option key={entry.id} value={entry.id} lang={entry.id}>
            {entry.name}
          </option>
        ))}
      </select>
    </label>
  );
}
