/**
 * The dataset's annotation guideline (doc 109): its conventions, written down, beside the
 * canvas. It opens by itself when it has text, so the next annotator reads it first.
 */

import { useEffect, useState, type JSX } from 'react';

import { getGuideline, saveGuideline } from '../api/quality';
import { useT } from '../i18n';
import '../quality.css';

export function GuidelinePanel({ datasetId }: { readonly datasetId: string }): JSX.Element {
  const { t } = useT();
  const [stored, setStored] = useState<string | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let live = true;
    setStored(null);
    setDraft(null);
    getGuideline(datasetId)
      .then((text) => live && setStored(text))
      .catch((cause: unknown) => live && setMessage(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [datasetId]);

  const text = draft ?? stored ?? '';
  const save = async (): Promise<void> => {
    try {
      setStored(await saveGuideline(datasetId, text));
      setDraft(null);
      setMessage(t('phrases.guideline.saved'));
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  };

  if (stored === null) return <p className="trainer__dim">{message || t('phrases.guideline.loading')}</p>;
  return (
    <details className="guideline" open={stored.trim() !== ''}>
      <summary>
        {t('phrases.guideline.title')}
        {stored.trim() === '' ? t('phrases.guideline.noneYet') : ''}
      </summary>
      <p className="guideline__hint">{t('phrases.guideline.hint')}</p>
      <textarea
        aria-label={t('phrases.guideline.title')}
        rows={5}
        value={text}
        placeholder={t('phrases.guideline.placeholder')}
        onChange={(event) => {
          setDraft(event.target.value);
          setMessage('');
        }}
      />
      <div className="guideline__actions">
        <button type="button" className="btn btn--small" disabled={draft === null} onClick={() => void save()}>
          {t('phrases.guideline.save')}
        </button>
        {message && <span className="trainer__dim" role="status">{message}</span>}
      </div>
    </details>
  );
}
