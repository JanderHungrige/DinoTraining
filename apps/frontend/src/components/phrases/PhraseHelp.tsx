/** The ideas behind phrases, explained where they are used (docs 105, 116). */

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
        <dt>{t('phrases.help.classesTerm')}</dt>
        <dd>{rich(t('phrases.help.classesText'))}</dd>
        <dt>{t('phrases.help.umbrellaTerm')}</dt>
        <dd>{rich(t('phrases.help.umbrellaText'))}</dd>
        <dt>{t('phrases.help.variationsTerm')}</dt>
        <dd>{rich(t('phrases.help.variationsText'))}</dd>
        <dt>{t('phrases.help.lookalikesTerm')}</dt>
        <dd>{rich(t('phrases.help.lookalikesText'))}</dd>
        <dt>{t('phrases.help.negativesTerm')}</dt>
        <dd>{rich(t('phrases.help.negativesText'))}</dd>
      </dl>
    </details>
  );
}
