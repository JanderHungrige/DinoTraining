/**
 * "This picture": for each phrase, all marked · not in this picture · clear (doc 105).
 * Saved at once — a check is not part of the picture's annotations.
 */

import type { JSX } from 'react';

import type { PhraseInfo, PhraseStatus, PictureStatus } from '../../api/phrases';
import { useT, type Key } from '../../i18n';

export interface PictureChecksProps {
  readonly phrases: readonly PhraseInfo[];
  readonly statuses: readonly PictureStatus[];
  readonly active: string;
  readonly disabled: boolean;
  readonly onMark: (phrase: string, status: PhraseStatus | null) => void;
}

const SAID: Record<PhraseStatus, Key> = { complete: 'phrases.checks.complete', absent: 'phrases.checks.absent' };

export function PictureChecks({ phrases, statuses, active, disabled, onMark }: PictureChecksProps): JSX.Element {
  const { t } = useT();
  const byText = new Map(statuses.map((s) => [s.text, s.status]));
  return (
    <>
      <table className="phrasechecks">
        <caption>{t('phrases.checks.caption')}</caption>
        <tbody>
          {phrases.map((phrase) => {
            const status = byText.get(phrase.text);
            return (
              <tr key={phrase.text} className={phrase.text === active ? 'phrasechecks__active' : ''}>
                <th scope="row">{phrase.text}</th>
                <td className={`phrasechecks__state phrasechecks__state--${status ?? 'unchecked'}`}>
                  {t(status ? SAID[status] : 'phrases.checks.unchecked')}
                </td>
                <td className="phrasechecks__actions">
                  <button type="button" className="btn btn--small" disabled={disabled || status === 'complete'} onClick={() => onMark(phrase.text, 'complete')}>
                    {t('phrases.checks.markComplete')}
                  </button>
                  <button type="button" className="btn btn--small" disabled={disabled || status === 'absent'} onClick={() => onMark(phrase.text, 'absent')}>
                    {t('phrases.checks.markAbsent')}
                  </button>
                  {status && (
                    <button type="button" className="btn btn--small" disabled={disabled} aria-label={t('phrases.checks.clearLabel', { phrase: phrase.text })} onClick={() => onMark(phrase.text, null)}>
                      {t('phrases.checks.clear')}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {phrases.length > 0 && <p className="phrasebar__note">{t('phrases.checks.restHint')}</p>}
    </>
  );
}
