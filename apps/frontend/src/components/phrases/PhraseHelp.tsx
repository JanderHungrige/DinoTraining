/** The three ideas behind phrases, explained where they are used (doc 105). */

import type { JSX, ReactNode } from 'react';

import { useT } from '../../i18n';

/** A catalogue paragraph with *emphasis* and `code`, rendered as such. */
function rich(text: string): ReactNode[] {
  return text.split(/(\*[^*]+\*|`[^`]+`)/).map((part, index) => {
    if (part.startsWith('*') && part.endsWith('*') && part.length > 1) return <em key={index}>{part.slice(1, -1)}</em>;
    if (part.startsWith('`') && part.endsWith('`') && part.length > 1) return <code key={index}>{part.slice(1, -1)}</code>;
    return part;
  });
}

export function PhraseHelp(): JSX.Element {
  const { t } = useT();
  return (
    <details className="phrasebar__help">
      <summary>{t('phrases.help.title')}</summary>
      <dl>
        <dt>{t('phrases.help.variationsTerm')}</dt>
        <dd>{rich(t('phrases.help.variationsText'))}</dd>
        <dt>{t('phrases.help.checksTerm')}</dt>
        <dd>{rich(t('phrases.help.checksText'))}</dd>
        <dt>{t('phrases.help.negativesTerm')}</dt>
        <dd>{rich(t('phrases.help.negativesText'))}</dd>
      </dl>
    </details>
  );
}
