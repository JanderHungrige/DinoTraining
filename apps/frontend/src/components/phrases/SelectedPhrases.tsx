/** The selected outline's phrases, and adding the active one (doc 105). */

import type { JSX } from 'react';

import type { PhraseInfo } from '../../api/phrases';
import { phrasesOf, refusal } from '../../lib/phraseEdit';
import type { CanvasBox } from '../../types/annotation';

export interface SelectedPhrasesProps {
  readonly box: CanvasBox;
  readonly number: number;
  readonly active: PhraseInfo | null;
  readonly disabled: boolean;
  readonly onAdd: (phrase: string) => void;
  readonly onRemove: (phrase: string) => void;
}

export function SelectedPhrases({ box, number, active, disabled, onAdd, onRemove }: SelectedPhrasesProps): JSX.Element {
  if (box.mask === undefined) {
    return <p className="phrasebar__note">#{number}: phrases go on outlines — make one from this box first.</p>;
  }
  const [own, ...rest] = phrasesOf(box);
  const why = active ? refusal(box, active) : '';
  const has = active !== null && [own, ...rest].includes(active.text);
  return (
    <div className="phrasebar__selected" aria-label={`Phrases of outline ${number}`} role="group">
      <span className="phrasebar__label">#{number} answers to</span>
      <span className="phrasechip phrasechip--fixed" title="Its class name is always one of its phrases">
        {own}
      </span>
      {rest.map((phrase) => (
        <span key={phrase} className="phrasechip">
          {phrase}
          <button type="button" className="phrasechip__remove" disabled={disabled} aria-label={`Remove ${phrase} from outline ${number}`} onClick={() => onRemove(phrase)}>
            ×
          </button>
        </span>
      ))}
      {active && !has && (
        <button type="button" className="btn btn--small" disabled={disabled || why !== ''} title={why || undefined} onClick={() => onAdd(active.text)}>
          Add “{active.text}”
        </button>
      )}
      {why && <span className="phrasebar__note">{why}</span>}
    </div>
  );
}
