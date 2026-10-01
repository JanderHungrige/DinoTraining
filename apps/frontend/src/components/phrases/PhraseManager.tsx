/**
 * Manage phrases (docs 105, 116): per class its variations and look-alikes; each umbrella
 * term with its classes; older sub-phrases (Wave 14) listed so they can be deleted. Nothing
 * here creates a class — classes are made in the annotation list.
 */

import { useState, type JSX } from 'react';

import { addPhrase, changePhrase, deletePhrase, type PhraseInfo } from '../../api/phrases';
import { useT } from '../../i18n';
import { phraseKey } from '../../lib/phraseEdit';

function list(text: string): string[] {
  return text.split(',').map((part) => part.trim()).filter(Boolean);
}

type Kind = 'class' | 'umbrella' | 'legacy';

export function kindOf(phrase: PhraseInfo): Kind {
  if (phrase.umbrella) return 'umbrella';
  return phrase.text === phraseKey(phrase.class_name) ? 'class' : 'legacy';
}

function DeleteButton({ datasetId, phrase, onDone, onProblem }: { readonly datasetId: string; readonly phrase: PhraseInfo; readonly onDone: () => void; readonly onProblem: (message: string) => void }): JSX.Element | null {
  const { t } = useT();
  const [confirming, setConfirming] = useState(false);
  if (phrase.id === null) return null;
  const id = phrase.id;
  const remove = async (): Promise<void> => {
    try {
      await deletePhrase(datasetId, id);
      onDone();
    } catch (cause) {
      onProblem(cause instanceof Error ? cause.message : String(cause));
    }
    setConfirming(false);
  };
  if (!confirming) {
    return (
      <button type="button" className="btn btn--small" title={t('phrases.manage.deleteHint')} onClick={() => setConfirming(true)}>
        {t('phrases.manage.delete')}
      </button>
    );
  }
  return (
    <>
      <span className="run__warn">{t('phrases.manage.deleteConfirm', { phrase: phrase.text })}</span>
      <button type="button" className="btn btn--small btn--danger" title={t('phrases.manage.deleteHint')} onClick={() => void remove()}>
        {t('phrases.manage.delete')}
      </button>
      <button type="button" className="btn btn--small" onClick={() => setConfirming(false)}>
        {t('common.cancel')}
      </button>
    </>
  );
}

function Row({ datasetId, phrase, onSaved }: { readonly datasetId: string; readonly phrase: PhraseInfo; readonly onSaved: () => void }): JSX.Element {
  const { t } = useT();
  const kind = kindOf(phrase);
  const [variants, setVariants] = useState<string | null>(null);
  const [confusable, setConfusable] = useState<string | null>(null);
  const [problem, setProblem] = useState('');
  const changed = variants !== null || confusable !== null;

  const save = async (): Promise<void> => {
    try {
      let id = phrase.id;
      if (id === null) {
        // A class's implicit phrase has no row yet: adding it with its variations makes one.
        id = (await addPhrase(datasetId, [phrase.text, ...list(variants ?? '')].join(', '), phrase.class_name)).id;
      } else if (variants !== null) {
        await changePhrase(datasetId, id, { variants: list(variants) });
      }
      if (confusable !== null && id !== null) await changePhrase(datasetId, id, { confusable: list(confusable) });
      setVariants(null);
      setConfusable(null);
      setProblem('');
      onSaved();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const note =
    kind === 'umbrella'
      ? t('phrases.manage.umbrella', { members: phrase.classes.join(', ') })
      : kind === 'legacy'
        ? t('phrases.manage.legacy', { name: phrase.class_name })
        : phrase.id === null
          ? t('phrases.manage.implicit', { name: phrase.class_name })
          : '';

  return (
    <li className={`phrasemanage__row phrasemanage__row--${kind}`}>
      <strong>{phrase.text}</strong>
      {note && <span className="trainer__dim"> — {note}</span>}
      {kind !== 'legacy' && (
        <>
          <label>
            {t('phrases.manage.variations')}
            <input value={variants ?? phrase.variants.join(', ')} placeholder={t('phrases.manage.variationsPlaceholder')} onChange={(e) => setVariants(e.target.value)} />
          </label>
          <label>
            {t('phrases.manage.confusable')}
            <input
              value={confusable ?? phrase.confusable.join(', ')}
              placeholder={t('phrases.manage.confusablePlaceholder')}
              title={t('phrases.manage.confusableHint')}
              onChange={(e) => setConfusable(e.target.value)}
            />
          </label>
          <button type="button" className="btn btn--small" disabled={!changed} onClick={() => void save()}>
            {t('phrases.manage.save')}
          </button>
        </>
      )}
      <DeleteButton datasetId={datasetId} phrase={phrase} onDone={onSaved} onProblem={setProblem} />
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </li>
  );
}

export function PhraseManager({ datasetId, phrases, onSaved }: { readonly datasetId: string; readonly phrases: readonly PhraseInfo[]; readonly onSaved: () => void }): JSX.Element {
  const { t } = useT();
  return (
    <details className="phrasemanage">
      <summary>{t('phrases.manage.title')}</summary>
      <p className="phrasebar__note">{t('phrases.manage.confusableHint')}</p>
      <ul>
        {phrases.map((phrase) => (
          <Row key={phrase.text} datasetId={datasetId} phrase={phrase} onSaved={onSaved} />
        ))}
      </ul>
    </details>
  );
}
