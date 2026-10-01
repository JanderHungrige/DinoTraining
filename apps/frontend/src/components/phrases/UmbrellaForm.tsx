/**
 * "+ Umbrella term" (doc 115/116): a general name over two or more classes, "screw" for m8
 * and m9. The only thing the phrase bar creates — classes are made in the annotation list.
 */

import { useState, type FormEvent, type JSX } from 'react';

import { addUmbrella } from '../../api/phrases';
import { useT } from '../../i18n';

export interface UmbrellaFormProps {
  readonly datasetId: string;
  /** The dataset's classes, as phrase keys. */
  readonly classes: readonly string[];
  readonly onAdded: (text: string) => void;
}

export function UmbrellaForm({ datasetId, classes, onAdded }: UmbrellaFormProps): JSX.Element {
  const { t } = useT();
  const [name, setName] = useState('');
  const [chosen, setChosen] = useState<ReadonlySet<string>>(new Set());
  const [problem, setProblem] = useState('');
  // Only classes that still exist count; a deleted one must not keep the button enabled.
  const members = classes.filter((c) => chosen.has(c));

  const toggle = (name: string): void =>
    setChosen((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });

  const add = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (!name.trim()) return;
    if (members.length < 2) {
      setProblem(t('phrases.umbrella.needTwo'));
      return;
    }
    try {
      const created = await addUmbrella(datasetId, name, members);
      setName('');
      setChosen(new Set());
      setProblem('');
      onAdded(created.text);
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  if (classes.length < 2) return <p className="phrasebar__note">{t('phrases.umbrella.noClasses')}</p>;
  return (
    <form className="phrasebar__add" onSubmit={(event) => void add(event)}>
      <label>
        {t('phrases.umbrella.addLabel')}
        <input
          value={name}
          placeholder={t('phrases.umbrella.placeholder')}
          aria-describedby="umbrella-hint"
          onChange={(event) => setName(event.target.value)}
        />
      </label>
      <fieldset className="phrasebar__members">
        <legend>{t('phrases.umbrella.classesLabel')}</legend>
        {classes.map((name) => (
          <label key={name}>
            <input type="checkbox" checked={chosen.has(name)} onChange={() => toggle(name)} /> {name}
          </label>
        ))}
      </fieldset>
      <button type="submit" className="btn btn--small" disabled={!name.trim()}>
        {t('phrases.umbrella.add')}
      </button>
      <span id="umbrella-hint" className="phrasebar__note">
        {t('phrases.umbrella.hint')}
      </span>
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </form>
  );
}
