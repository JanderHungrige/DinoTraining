/**
 * The phrase bar (docs 105, 116): an overview of the dataset's classes and umbrella terms
 * with their outline counts, "+ Umbrella term", Manage phrases, the explanation — and,
 * folded, the picture checks for imported or partly annotated datasets.
 *
 * Nothing here creates a class: every class is made in the annotation list and is its own
 * phrase (Jan, 2026-09-30: "+ phrase" as a class was doubled and confusing).
 */

import { useCallback, useState, type JSX } from 'react';

import type { PhraseStatus } from '../../api/phrases';
import type { PicturePhrases } from '../../hooks/usePicturePhrases';
import { usePhraseKeys } from '../../hooks/usePhraseKeys';
import { useT } from '../../i18n';
import { PartialChecks } from './PartialChecks';
import { PhraseHelp } from './PhraseHelp';
import { kindOf, PhraseManager } from './PhraseManager';
import { UmbrellaForm } from './UmbrellaForm';
import '../../phrases.css';

export interface PhraseBarProps {
  readonly datasetId: string;
  readonly pictures: PicturePhrases;
  /** SAM 3 and "keep all options open" start with it open; other targets folded. */
  readonly open: boolean;
  readonly disabled: boolean;
}

export function PhraseBar({ datasetId, pictures, open, disabled }: PhraseBarProps): JSX.Element {
  const { phrases } = pictures;
  const { t } = useT();
  const [activeChoice, setActiveChoice] = useState('');
  const [checksOpen, setChecksOpen] = useState(false);
  const active = phrases.find((p) => p.text === activeChoice) ?? phrases[0] ?? null;
  const classes = [...new Set(phrases.filter((p) => kindOf(p) === 'class').map((p) => p.text))];

  const pick = useCallback((index: number) => setActiveChoice(phrases[index]?.text ?? ''), [phrases]);
  const markActive = useCallback(
    (status: PhraseStatus) => active && void pictures.mark(active.text, status),
    [active, pictures],
  );
  // Only while the checks are open: folded, "a" and "n" must not mark a picture unseen.
  usePhraseKeys(!disabled && checksOpen, phrases.length, pick, markActive);

  const title = (variants: readonly string[], members: readonly string[] | null): string => {
    const over = members ? `${t('phrases.bar.over', { members: members.join(', ') })} · ` : '';
    return over + (variants.length ? t('phrases.bar.also', { variants: variants.join(', ') }) : t('phrases.bar.noVariations'));
  };

  return (
    <details className="phrasebar" open={open}>
      <summary>{open ? t('phrases.bar.title') : t('phrases.bar.titleOptional')}</summary>
      <div className="phrasebar__chips" role="group" aria-label={t('phrases.bar.chipsLabel')}>
        {phrases.map((phrase, index) => (
          <button
            key={phrase.text}
            type="button"
            className={`phrasechip phrasechip--${kindOf(phrase)}${phrase.text === active?.text ? ' phrasechip--active' : ''}`}
            aria-pressed={phrase.text === active?.text}
            title={title(phrase.variants, phrase.umbrella ? phrase.classes : null)}
            onClick={() => setActiveChoice(phrase.text)}
          >
            {checksOpen && index < 9 && <span className="phrasechip__key">{index + 1}</span>}
            {phrase.text} <span className="phrasechip__count">{phrase.instances}</span>
          </button>
        ))}
      </div>
      <UmbrellaForm datasetId={datasetId} classes={classes} onAdded={(text) => { setActiveChoice(text); pictures.reload(); }} />
      {pictures.error && <p className="run__warn" role="alert">{pictures.error}</p>}
      <PhraseManager datasetId={datasetId} phrases={phrases} onSaved={pictures.reload} />
      <PhraseHelp />
      <PartialChecks
        datasetId={datasetId}
        phrases={phrases}
        statuses={pictures.statuses}
        active={active?.text ?? ''}
        disabled={disabled}
        open={checksOpen}
        onOpenChange={setChecksOpen}
        onMark={(phrase, status) => void pictures.mark(phrase, status)}
        onMarked={pictures.reload}
      />
    </details>
  );
}
