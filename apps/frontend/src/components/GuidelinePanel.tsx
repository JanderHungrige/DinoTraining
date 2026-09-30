/**
 * The dataset's annotation guideline (doc 109): its conventions, written down, beside the
 * canvas. It opens by itself when it has text, so the next annotator reads it first.
 */

import { useEffect, useState, type JSX } from 'react';

import { getGuideline, saveGuideline } from '../api/quality';
import '../quality.css';

export function GuidelinePanel({ datasetId }: { readonly datasetId: string }): JSX.Element {
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
      setMessage('Saved.');
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    }
  };

  if (stored === null) return <p className="trainer__dim">{message || 'Loading the guideline…'}</p>;
  return (
    <details className="guideline" open={stored.trim() !== ''}>
      <summary>Annotation guideline{stored.trim() === '' ? ' (none yet)' : ''}</summary>
      <p className="guideline__hint">
        Write down the conventions, so every picture is annotated the same way: what counts as
        part of an object, when to mark it unclear, which name is right.
      </p>
      <textarea
        aria-label="Annotation guideline"
        rows={5}
        value={text}
        placeholder={'Rings: outline with the hole filled.\nMore than half hidden: unclear.'}
        onChange={(event) => {
          setDraft(event.target.value);
          setMessage('');
        }}
      />
      <div className="guideline__actions">
        <button type="button" className="btn btn--small" disabled={draft === null} onClick={() => void save()}>
          Save guideline
        </button>
        {message && <span className="trainer__dim" role="status">{message}</span>}
      </div>
    </details>
  );
}
