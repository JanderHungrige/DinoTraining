/**
 * The phrase bar (doc 105): the dataset's phrases as chips, keys 1–9 to switch, "+ phrase"
 * with comma variations, the selected outline's phrases, and this picture's checks.
 *
 * A bar rather than a dropdown: for SAM 3 the vocabulary *is* the task, so it stays in view
 * with its counts, and both per-picture jobs — which phrases an outline answers to, which
 * phrases the picture was checked for — need it at hand.
 */

import { useCallback, useState, type FormEvent, type JSX } from 'react';

import { addPhrase, type PhraseStatus } from '../../api/phrases';
import type { PicturePhrases } from '../../hooks/usePicturePhrases';
import { usePhraseKeys } from '../../hooks/usePhraseKeys';
import { phraseKey, withPhrase, withoutPhrase } from '../../lib/phraseEdit';
import type { NumberedBox } from '../../lib/boxReview';
import type { CanvasBox } from '../../types/annotation';
import { PhraseHelp } from './PhraseHelp';
import { PhraseManager } from './PhraseManager';
import { PictureChecks } from './PictureChecks';
import { SelectedPhrases } from './SelectedPhrases';
import '../../phrases.css';

export interface PhraseBarProps {
  readonly datasetId: string;
  readonly items: readonly NumberedBox[];
  readonly selectedId: string | null;
  readonly pictures: PicturePhrases;
  readonly onBoxesChange: (boxes: CanvasBox[]) => void;
  /** SAM 3 and "keep all options open" start with it open; other targets folded. */
  readonly open: boolean;
  readonly disabled: boolean;
}

export function PhraseBar(props: PhraseBarProps): JSX.Element {
  const { datasetId, items, selectedId, pictures, disabled } = props;
  const { phrases } = pictures;
  const [activeChoice, setActiveChoice] = useState('');
  const [draft, setDraft] = useState('');
  const [problem, setProblem] = useState('');
  const selected = items.find((item) => item.box.id === selectedId) ?? null;
  const active = phrases.find((p) => p.text === activeChoice) ?? phrases[0] ?? null;

  const pick = useCallback((index: number) => setActiveChoice(phrases[index]?.text ?? ''), [phrases]);
  const markActive = useCallback(
    (status: PhraseStatus) => active && void pictures.mark(active.text, status),
    [active, pictures],
  );
  usePhraseKeys(!disabled, phrases.length, pick, markActive);

  const edit = (change: (box: CanvasBox) => CanvasBox): void => {
    if (!selected) return;
    props.onBoxesChange(items.map((item) => (item.box.id === selected.box.id ? change(item.box) : item.box)));
  };

  const add = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    if (!draft.trim()) return;
    const className = selected?.box.mask ? selected.box.text : undefined;
    try {
      const created = await addPhrase(datasetId, draft, className);
      setDraft('');
      setProblem('');
      setActiveChoice(created.text);
      pictures.reload();
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <details className="phrasebar" open={props.open}>
      <summary>{props.open ? 'Phrases' : 'Phrases (optional)'}</summary>
      <div className="phrasebar__chips" role="group" aria-label="Phrases — keys 1–9 pick one">
        {phrases.map((phrase, index) => (
          <button
            key={phrase.text}
            type="button"
            className={`phrasechip${phrase.text === active?.text ? ' phrasechip--active' : ''}`}
            aria-pressed={phrase.text === active?.text}
            title={phrase.variants.length ? `Also: ${phrase.variants.join(', ')}` : 'No variations yet'}
            onClick={() => setActiveChoice(phrase.text)}
          >
            {index < 9 && <span className="phrasechip__key">{index + 1}</span>}
            {phrase.text} <span className="phrasechip__count">{phrase.instances}</span>
          </button>
        ))}
      </div>
      <form className="phrasebar__add" onSubmit={(event) => void add(event)}>
        <label>
          + phrase
          <input
            value={draft}
            placeholder="signal, railway signal, light signal"
            aria-describedby="phrasebar-add-hint"
            onChange={(event) => setDraft(event.target.value)}
          />
        </label>
        <button type="submit" className="btn btn--small" disabled={!draft.trim()}>
          Add
        </button>
        <span id="phrasebar-add-hint" className="phrasebar__note">
          Commas separate variations of one phrase.
          {selected?.box.mask ? ` It joins class ${phraseKey(selected.box.text ?? '')}.` : ''}
        </span>
      </form>
      {problem && <p className="run__warn" role="alert">{problem}</p>}
      {pictures.error && <p className="run__warn" role="alert">{pictures.error}</p>}
      {selected && (
        <SelectedPhrases
          box={selected.box}
          number={selected.number}
          active={active}
          disabled={disabled}
          onAdd={(phrase) => edit((box) => withPhrase(box, phrase))}
          onRemove={(phrase) => edit((box) => withoutPhrase(box, phrase))}
        />
      )}
      <PictureChecks
        phrases={phrases}
        statuses={pictures.statuses}
        active={active?.text ?? ''}
        disabled={disabled}
        onMark={(phrase, status) => void pictures.mark(phrase, status)}
      />
      <p className="phrasebar__note">Keys: 1–9 pick a phrase · A all marked · N not in this picture.</p>
      <PhraseManager datasetId={datasetId} phrases={phrases} onSaved={pictures.reload} />
      <PhraseHelp />
    </details>
  );
}
