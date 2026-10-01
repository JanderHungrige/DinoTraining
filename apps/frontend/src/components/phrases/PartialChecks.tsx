/**
 * The picture checks, folded (doc 116): a saved picture counts as complete for the classes
 * it has then (doc 117), so checking by hand is only for imported or partly annotated
 * datasets. The keys work only while this is open — folded, "a" and "n" do nothing here.
 */

import { useState, type FormEvent, type JSX } from 'react';

import { markTheRest, type PhraseInfo, type PhraseStatus, type PictureStatus } from '../../api/phrases';
import { useT } from '../../i18n';
import { PictureChecks } from './PictureChecks';

export interface PartialChecksProps {
  readonly datasetId: string;
  readonly phrases: readonly PhraseInfo[];
  readonly statuses: readonly PictureStatus[];
  readonly active: string;
  readonly disabled: boolean;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onMark: (phrase: string, status: PhraseStatus | null) => void;
  readonly onMarked: () => void;
}

function MarkRest({ datasetId, phrases, onMarked }: Pick<PartialChecksProps, 'datasetId' | 'phrases' | 'onMarked'>): JSX.Element {
  const { t } = useT();
  const [override, setOverride] = useState('');
  const [said, setSaid] = useState('');
  const phrase = override || phrases[0]?.text || '';

  const fill = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    try {
      const done = await markTheRest(datasetId, phrase);
      setSaid(t('phrases.checks.marked', { complete: done.complete, absent: done.absent }));
      onMarked();
    } catch (cause) {
      setSaid(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <form className="phrasebar__add" onSubmit={(event) => void fill(event)}>
      <label>
        {t('phrases.checks.markRestFor')}
        <select value={phrase} onChange={(event) => setOverride(event.target.value)}>
          {phrases.map((p) => (
            <option key={p.text} value={p.text}>
              {p.text}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="btn btn--small" title={t('phrases.checks.markRestHint')} disabled={!phrase}>
        {t('phrases.checks.markRest')}
      </button>
      {said && <span className="trainer__dim" role="status">{said}</span>}
    </form>
  );
}

export function PartialChecks(props: PartialChecksProps): JSX.Element {
  const { t } = useT();
  return (
    <details className="phrasechecks__fold" open={props.open} onToggle={(event) => props.onOpenChange(event.currentTarget.open)}>
      <summary>{t('phrases.checks.section')}</summary>
      <p className="phrasebar__note">{t('phrases.checks.intro')}</p>
      {props.open && (
        <>
          <PictureChecks
            phrases={props.phrases}
            statuses={props.statuses}
            active={props.active}
            disabled={props.disabled}
            onMark={props.onMark}
          />
          <p className="phrasebar__note">{t('phrases.checks.keys')}</p>
          <MarkRest datasetId={props.datasetId} phrases={props.phrases} onMarked={props.onMarked} />
        </>
      )}
    </details>
  );
}
