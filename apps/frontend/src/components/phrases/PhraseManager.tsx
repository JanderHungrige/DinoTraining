/**
 * Manage phrases (doc 105): each phrase's variations and look-alikes, edited as
 * comma-separated text and saved at once. The store's refusals come back at the row.
 */

import { useState, type JSX } from 'react';

import { addPhrase, changePhrase, markTheRest, type PhraseInfo } from '../../api/phrases';
import { useT } from '../../i18n';

function list(text: string): string[] {
  return text.split(',').map((part) => part.trim()).filter(Boolean);
}

function Row({ datasetId, phrase, onSaved }: { readonly datasetId: string; readonly phrase: PhraseInfo; readonly onSaved: () => void }): JSX.Element {
  const { t } = useT();
  const [variants, setVariants] = useState<string | null>(null);
  const [confusable, setConfusable] = useState<string | null>(null);
  const [problem, setProblem] = useState('');
  const [filled, setFilled] = useState('');
  const shownVariants = variants ?? phrase.variants.join(', ');
  const shownConfusable = confusable ?? phrase.confusable.join(', ');
  const changed = variants !== null || confusable !== null;

  const save = async (): Promise<void> => {
    try {
      let id = phrase.id;
      if (id === null) {
        // A class's implicit phrase has no row yet: adding it with its variations makes one.
        const text = [phrase.text, ...list(variants ?? '')].join(', ');
        id = (await addPhrase(datasetId, text, phrase.class_name)).id;
      } else if (variants !== null) {
        await changePhrase(datasetId, id, { variants: list(variants) });
      }
      if (confusable !== null && id !== null) {
        await changePhrase(datasetId, id, { confusable: list(confusable) });
      }
      setVariants(null);
      setConfusable(null);
      setProblem('');
      onSaved();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const fill = async (): Promise<void> => {
    try {
      const done = await markTheRest(datasetId, phrase.text);
      setProblem('');
      setFilled(t('phrases.manage.marked', { complete: done.complete, absent: done.absent }));
      onSaved();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <li className="phrasemanage__row">
      <strong>{phrase.text}</strong> <span className="trainer__dim">({phrase.class_name})</span>
      <label>
        {t('phrases.manage.variations')}
        <input value={shownVariants} placeholder={t('phrases.manage.variationsPlaceholder')} onChange={(e) => setVariants(e.target.value)} />
      </label>
      <label>
        {t('phrases.manage.confusable')}
        <input value={shownConfusable} placeholder={t('phrases.manage.confusablePlaceholder')} onChange={(e) => setConfusable(e.target.value)} />
      </label>
      <button type="button" className="btn btn--small" disabled={!changed} onClick={() => void save()}>
        {t('phrases.manage.save')}
      </button>
      <button
        type="button"
        className="btn btn--small"
        title={t('phrases.manage.markRestHint')}
        onClick={() => void fill()}
      >
        {t('phrases.manage.markRest')}
      </button>
      {filled && <span className="trainer__dim" role="status">{filled}</span>}
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </li>
  );
}

export function PhraseManager({ datasetId, phrases, onSaved }: { readonly datasetId: string; readonly phrases: readonly PhraseInfo[]; readonly onSaved: () => void }): JSX.Element {
  const { t } = useT();
  return (
    <details className="phrasemanage">
      <summary>{t('phrases.manage.title')}</summary>
      <ul>
        {phrases.map((phrase) => (
          <Row key={phrase.text} datasetId={datasetId} phrase={phrase} onSaved={onSaved} />
        ))}
      </ul>
    </details>
  );
}
