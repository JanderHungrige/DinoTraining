/**
 * Manage phrases (doc 105): each phrase's variations and look-alikes, edited as
 * comma-separated text and saved at once. The store's refusals come back at the row.
 */

import { useState, type JSX } from 'react';

import { addPhrase, changePhrase, markTheRest, type PhraseInfo } from '../../api/phrases';

function list(text: string): string[] {
  return text.split(',').map((part) => part.trim()).filter(Boolean);
}

function Row({ datasetId, phrase, onSaved }: { readonly datasetId: string; readonly phrase: PhraseInfo; readonly onSaved: () => void }): JSX.Element {
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
      setFilled(`Marked ${done.complete} all marked, ${done.absent} not in this picture.`);
      onSaved();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <li className="phrasemanage__row">
      <strong>{phrase.text}</strong> <span className="trainer__dim">({phrase.class_name})</span>
      <label>
        Variations
        <input value={shownVariants} placeholder="railway signal, light signal" onChange={(e) => setVariants(e.target.value)} />
      </label>
      <label>
        Not to be confused with
        <input value={shownConfusable} placeholder="street lamp, traffic sign" onChange={(e) => setConfusable(e.target.value)} />
      </label>
      <button type="button" className="btn btn--small" disabled={!changed} onClick={() => void save()}>
        Save
      </button>
      <button
        type="button"
        className="btn btn--small"
        title="Only if every picture is fully annotated for this phrase: each unchecked picture becomes 'all marked' where it has an outline of it, 'not in this picture' where it has none."
        onClick={() => void fill()}
      >
        Mark the rest
      </button>
      {filled && <span className="trainer__dim" role="status">{filled}</span>}
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </li>
  );
}

export function PhraseManager({ datasetId, phrases, onSaved }: { readonly datasetId: string; readonly phrases: readonly PhraseInfo[]; readonly onSaved: () => void }): JSX.Element {
  return (
    <details className="phrasemanage">
      <summary>Manage phrases</summary>
      <ul>
        {phrases.map((phrase) => (
          <Row key={phrase.text} datasetId={datasetId} phrase={phrase} onSaved={onSaved} />
        ))}
      </ul>
    </details>
  );
}
