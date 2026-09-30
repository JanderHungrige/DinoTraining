/**
 * "This picture": for each phrase, all marked · not in this picture · clear (doc 105).
 * Saved at once — a check is not part of the picture's annotations.
 */

import type { JSX } from 'react';

import type { PhraseInfo, PhraseStatus, PictureStatus } from '../../api/phrases';

export interface PictureChecksProps {
  readonly phrases: readonly PhraseInfo[];
  readonly statuses: readonly PictureStatus[];
  readonly active: string;
  readonly disabled: boolean;
  readonly onMark: (phrase: string, status: PhraseStatus | null) => void;
}

const SAID: Record<PhraseStatus, string> = { complete: 'all marked', absent: 'not in this picture' };

export function PictureChecks({ phrases, statuses, active, disabled, onMark }: PictureChecksProps): JSX.Element {
  const byText = new Map(statuses.map((s) => [s.text, s.status]));
  return (
    <table className="phrasechecks">
      <caption>This picture</caption>
      <tbody>
        {phrases.map((phrase) => {
          const status = byText.get(phrase.text);
          return (
            <tr key={phrase.text} className={phrase.text === active ? 'phrasechecks__active' : ''}>
              <th scope="row">{phrase.text}</th>
              <td className={`phrasechecks__state phrasechecks__state--${status ?? 'unchecked'}`}>
                {status ? SAID[status] : 'not checked'}
              </td>
              <td className="phrasechecks__actions">
                <button type="button" className="btn btn--small" disabled={disabled || status === 'complete'} onClick={() => onMark(phrase.text, 'complete')}>
                  All marked
                </button>
                <button type="button" className="btn btn--small" disabled={disabled || status === 'absent'} onClick={() => onMark(phrase.text, 'absent')}>
                  Not in this picture
                </button>
                {status && (
                  <button type="button" className="btn btn--small" disabled={disabled} aria-label={`Clear the check for ${phrase.text}`} onClick={() => onMark(phrase.text, null)}>
                    clear
                  </button>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
