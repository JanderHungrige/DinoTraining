/**
 * The second-look bar (doc 109): start a sample, judge each picture, read the figure.
 * Above about one in ten needing a change, the conventions are unclear — fix the guideline
 * before annotating more.
 */

import type { JSX } from 'react';

import type { SecondLook as SecondLookState } from '../hooks/useSecondLook';
import '../quality.css';

export interface SecondLookProps {
  readonly look: SecondLookState;
  readonly currentImage: string | null;
  readonly disabled: boolean;
}

export function figure(changed: number, reviewed: number, rate: number | null): string {
  if (rate === null) return 'Nothing judged yet.';
  return `${changed} of ${reviewed} needed a change (${Math.round(rate * 100)} %)`;
}

export function SecondLook({ look, currentImage, disabled }: SecondLookProps): JSX.Element {
  const { info } = look;
  const inSample = info !== null && currentImage !== null && info.sample.includes(currentImage);
  const verdict = inSample ? info.verdicts[currentImage] : undefined;
  return (
    <div className="secondlook" role="group" aria-label="Second look">
      {look.active ? (
        <>
          <strong>Second look</strong>
          <span>
            {info?.reviewed ?? 0} of {info?.sample.length ?? 0} judged · {info ? figure(info.changed, info.reviewed, info.rate) : ''}
          </span>
          {inSample && currentImage && (
            <>
              <button type="button" className={`btn btn--small${verdict === 'right' ? ' secondlook__on' : ''}`} disabled={disabled} onClick={() => look.judge(currentImage, 'right')}>
                Looks right
              </button>
              <button type="button" className={`btn btn--small${verdict === 'changed' ? ' secondlook__on' : ''}`} disabled={disabled} onClick={() => look.judge(currentImage, 'changed')}>
                Needed a change
              </button>
            </>
          )}
          <button type="button" className="btn btn--small" onClick={look.stop}>
            End second look
          </button>
        </>
      ) : (
        <>
          <button type="button" className="btn btn--small" disabled={disabled} onClick={look.start} title="Show a random 5 % of the annotated pictures again, to judge them fresh">
            Second look
          </button>
          {info && info.reviewed > 0 && <span className="trainer__dim">Last time: {figure(info.changed, info.reviewed, info.rate)}</span>}
        </>
      )}
      {look.error && <span className="run__warn" role="alert">{look.error}</span>}
    </div>
  );
}
