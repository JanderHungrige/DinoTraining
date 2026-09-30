/** The selected outline's phrases, and adding the active one (doc 105). */

import type { JSX } from 'react';

import type { PhraseInfo } from '../../api/phrases';
import { phrasesOf, refusal } from '../../lib/phraseEdit';
import type { CanvasBox } from '../../types/annotation';
import { useT } from '../../i18n';

export interface SelectedPhrasesProps {
  readonly box: CanvasBox;
  readonly number: number;
  readonly active: PhraseInfo | null;
  readonly disabled: boolean;
  readonly onAdd: (phrase: string) => void;
  readonly onRemove: (phrase: string) => void;
}

export function SelectedPhrases({ box, number, active, disabled, onAdd, onRemove }: SelectedPhrasesProps): JSX.Element {
  const { t } = useT();
  if (box.mask === undefined) {
    return <p className="phrasebar__note">{t('phrases.selected.needsOutline', { number })}</p>;
  }
  const [own, ...rest] = phrasesOf(box);
  // refusal() decides; the reason is worded here, where the language is known.
  const why = active && refusal(box, active)
    ? t('phrases.selected.otherClass', { phrase: active.text, className: active.class_name, outline: box.text ?? t('phrases.selected.unnamed') })
    : '';
  const has = active !== null && [own, ...rest].includes(active.text);
  return (
    <div className="phrasebar__selected" aria-label={t('phrases.selected.groupLabel', { number })} role="group">
      <span className="phrasebar__label">{t('phrases.selected.answersTo', { number })}</span>
      <span className="phrasechip phrasechip--fixed" title={t('phrases.selected.classAlways')}>
        {own}
      </span>
      {rest.map((phrase) => (
        <span key={phrase} className="phrasechip">
          {phrase}
          <button type="button" className="phrasechip__remove" disabled={disabled} aria-label={t('phrases.selected.remove', { phrase, number })} onClick={() => onRemove(phrase)}>
            ×
          </button>
        </span>
      ))}
      {active && !has && (
        <button type="button" className="btn btn--small" disabled={disabled || why !== ''} title={why || undefined} onClick={() => onAdd(active.text)}>
          {t('phrases.selected.add', { phrase: active.text })}
        </button>
      )}
      {why && <span className="phrasebar__note">{why}</span>}
    </div>
  );
}
