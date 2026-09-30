/**
 * "m10 is new — does it occur in the pictures already saved?" (doc 118).
 *
 * A banner, not a modal: the user may be in the middle of an outline. Asked for every class
 * with pictures saved before it (doc 117). "It does not occur there" marks them absent;
 * "Review them later" leaves them unknown — left out for that class — and keeps a one-line
 * reminder with "Review for …" (doc 119).
 */

import { useEffect, useState, type JSX } from 'react';

import { getCompleteness, markAbsentInOlder, type ClassCompleteness } from '../api/phrases';
import { usePersistentState } from '../hooks/usePersistentState';
import { useT } from '../i18n';
import { isStringArray } from '../lib/persisted';
import '../phrases.css';

export interface NewClassQuestionProps {
  readonly datasetId: string;
  /** Changes whenever the vocabulary might have: the question looks again. */
  readonly watch: string;
  readonly onReview?: (className: string) => void;
}

export function NewClassQuestion({ datasetId, watch, onReview }: NewClassQuestionProps): JSX.Element | null {
  const { t, tp } = useT();
  const [found, setFound] = useState<Record<string, ClassCompleteness>>({});
  const [said, setSaid] = useState('');
  const [problem, setProblem] = useState('');
  const [generation, setGeneration] = useState(0);
  // Per viewer, per dataset: which classes were answered "review later". A convenience only.
  const [later, setLater] = usePersistentState<string[]>(`studio.reviewLater.${datasetId}`, [], isStringArray);

  useEffect(() => {
    let live = true;
    getCompleteness(datasetId)
      .then((next) => live && setFound(next))
      .catch((cause: unknown) => live && setProblem(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [datasetId, watch, generation]);

  const open = Object.entries(found).filter(([, info]) => info.unknown > 0);
  if (open.length === 0 && !said && !problem) return null;

  const notThere = async (name: string, count: number): Promise<void> => {
    try {
      await markAbsentInOlder(datasetId, name);
      setSaid(tp('studio.newClass.marked', count, { name }));
      setGeneration((n) => n + 1);
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <section className="newclass" aria-label={t('studio.newClass.label')}>
      {open.map(([name, info]) =>
        later.includes(name) ? (
          <p key={name} className="newclass__line">
            {tp('studio.newClass.pending', info.unknown, { name })}{' '}
            {onReview && (
              <button type="button" className="btn btn--small" onClick={() => onReview(name)}>
                {t('studio.newClass.review', { name })}
              </button>
            )}
          </p>
        ) : (
          <div key={name} className="newclass__ask" role="alertdialog" aria-label={t('studio.newClass.label')}>
            <p>
              <strong>{tp('studio.newClass.question', info.unknown, { name })}</strong>{' '}
              {t('studio.newClass.why', { name })}
            </p>
            <button type="button" className="btn btn--small" onClick={() => void notThere(name, info.unknown)}>
              {t('studio.newClass.notThere')}
            </button>
            <button type="button" className="btn btn--small" onClick={() => setLater([...later, name])}>
              {t('studio.newClass.later')}
            </button>
          </div>
        ),
      )}
      {said && <p className="trainer__dim" role="status">{said}</p>}
      {problem && <p className="run__warn" role="alert">{problem}</p>}
    </section>
  );
}
