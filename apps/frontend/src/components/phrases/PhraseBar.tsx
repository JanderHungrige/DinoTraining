/**
 * The phrase bar (doc 105): the dataset's phrases as chips, keys 1–9 to switch, "+ phrase"
 * with comma variations, the selected outline's phrases, and this picture's checks.
 *
 * A bar rather than a dropdown: for SAM 3 the vocabulary *is* the task, so it stays in view
 * with its counts, and both per-picture jobs — which phrases an outline answers to, which
 * phrases the picture was checked for — need it at hand.
 */

import { useCallback, useState, type JSX } from 'react';

import type { PhraseStatus } from '../../api/phrases';
import type { PicturePhrases } from '../../hooks/usePicturePhrases';
import { usePhraseKeys } from '../../hooks/usePhraseKeys';
import { phraseKey, withPhrase, withoutPhrase } from '../../lib/phraseEdit';
import type { NumberedBox } from '../../lib/boxReview';
import type { CanvasBox } from '../../types/annotation';
import { useT } from '../../i18n';
import { AddPhraseForm } from './AddPhraseForm';
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
  const { t } = useT();
  const [activeChoice, setActiveChoice] = useState('');
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


  return (
    <details className="phrasebar" open={props.open}>
      <summary>{props.open ? t('phrases.bar.title') : t('phrases.bar.titleOptional')}</summary>
      <div className="phrasebar__chips" role="group" aria-label={t('phrases.bar.chipsLabel')}>
        {phrases.map((phrase, index) => (
          <button
            key={phrase.text}
            type="button"
            className={`phrasechip${phrase.text === active?.text ? ' phrasechip--active' : ''}`}
            aria-pressed={phrase.text === active?.text}
            title={phrase.variants.length ? t('phrases.bar.also', { variants: phrase.variants.join(', ') }) : t('phrases.bar.noVariations')}
            onClick={() => setActiveChoice(phrase.text)}
          >
            {index < 9 && <span className="phrasechip__key">{index + 1}</span>}
            {phrase.text} <span className="phrasechip__count">{phrase.instances}</span>
          </button>
        ))}
      </div>
      <AddPhraseForm
        datasetId={datasetId}
        phrases={phrases}
        selectedClass={selected?.box.mask ? phraseKey(selected.box.text ?? '') : ''}
        onAdded={(text) => {
          setActiveChoice(text);
          pictures.reload();
        }}
      />
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
      <p className="phrasebar__note">{t('phrases.bar.keys')}</p>
      <PhraseManager datasetId={datasetId} phrases={phrases} onSaved={pictures.reload} />
      <PhraseHelp />
    </details>
  );
}
