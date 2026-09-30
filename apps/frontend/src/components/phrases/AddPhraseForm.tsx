/**
 * "+ phrase" (doc 105, amended): the phrase, and which class it belongs to — said out
 * loud. Before, the class was implied by whichever outline happened to be selected, so
 * with more than one class nobody could tell where a new phrase went (Jan, 2026-09-30).
 */

import { useState, type FormEvent, type JSX } from 'react';

import { addPhrase, type PhraseInfo } from '../../api/phrases';
import { useT } from '../../i18n';
import { phraseKey } from '../../lib/phraseEdit';

export interface AddPhraseFormProps {
  readonly datasetId: string;
  readonly phrases: readonly PhraseInfo[];
  /** The selected outline's class, the natural default; '' when none is selected. */
  readonly selectedClass: string;
  readonly onAdded: (text: string) => void;
}

/** The phrase itself, as the backend will store it: the first comma part. */
function mainPhrase(draft: string): string {
  return phraseKey(draft.split(',')[0] ?? '');
}

export function AddPhraseForm({ datasetId, phrases, selectedClass, onAdded }: AddPhraseFormProps): JSX.Element {
  const { t } = useT();
  const [draft, setDraft] = useState('');
  const [problem, setProblem] = useState('');
  // Only the user's choice is stored; the default follows the selection (CLAUDE.md).
  const [override, setOverride] = useState<string | null>(null);
  const classes = [...new Set(phrases.map((p) => p.class_name))].sort();
  const chosen = override ?? (classes.includes(selectedClass) ? selectedClass : '');

  const add = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (!draft.trim()) return;
    try {
      const created = await addPhrase(datasetId, draft, chosen || undefined);
      setDraft('');
      setOverride(null);
      setProblem('');
      onAdded(created.text);
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const name = mainPhrase(draft) || '…';
  return (
    <form className="phrasebar__add" onSubmit={(event) => void add(event)}>
      <label>
        {t('phrases.bar.addLabel')}
        <input
          value={draft}
          placeholder={t('phrases.bar.addPlaceholder')}
          aria-describedby="phrasebar-add-hint"
          onChange={(event) => setDraft(event.target.value)}
        />
      </label>
      <label>
        {t('phrases.bar.classLabel')}
        <select value={chosen} onChange={(event) => setOverride(event.target.value)}>
          <option value="">{t('phrases.bar.ownClass')}</option>
          {classes.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="btn btn--small" disabled={!draft.trim()}>
        {t('phrases.bar.addButton')}
      </button>
      <span id="phrasebar-add-hint" className="phrasebar__note">
        {t('phrases.bar.addHint')}
        {chosen ? t('phrases.bar.joinsClass', { name: chosen }) : t('phrases.bar.ownClassHint', { name })}
      </span>
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </form>
  );
}
