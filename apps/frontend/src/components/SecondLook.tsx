/**
 * The second-look bar (doc 109): start a sample, judge each picture, read the figure.
 * Above about one in ten needing a change, the conventions are unclear — fix the guideline
 * before annotating more.
 */

import type { JSX } from 'react';

import type { SecondLook as SecondLookState } from '../hooks/useSecondLook';
import { useT, type Translator } from '../i18n';
import '../quality.css';

export interface SecondLookProps {
  readonly look: SecondLookState;
  readonly currentImage: string | null;
  readonly disabled: boolean;
}

export function figure(changed: number, reviewed: number, rate: number | null, { t }: Translator): string {
  if (rate === null) return t('phrases.secondLook.nothingYet');
  return t('phrases.secondLook.figure', { changed, reviewed, percent: Math.round(rate * 100) });
}

export function SecondLook({ look, currentImage, disabled }: SecondLookProps): JSX.Element {
  const translator = useT();
  const { t } = translator;
  const { info } = look;
  const inSample = info !== null && currentImage !== null && info.sample.includes(currentImage);
  const verdict = inSample ? info.verdicts[currentImage] : undefined;
  return (
    <div className="secondlook" role="group" aria-label={t('phrases.secondLook.title')}>
      {look.active ? (
        <>
          <strong>{t('phrases.secondLook.title')}</strong>
          <span>
            {t('phrases.secondLook.judged', { reviewed: info?.reviewed ?? 0, total: info?.sample.length ?? 0 })} ·{' '}
            {info ? figure(info.changed, info.reviewed, info.rate, translator) : ''}
          </span>
          {inSample && currentImage && (
            <>
              <button type="button" className={`btn btn--small${verdict === 'right' ? ' secondlook__on' : ''}`} disabled={disabled} onClick={() => look.judge(currentImage, 'right')}>
                {t('phrases.secondLook.right')}
              </button>
              <button type="button" className={`btn btn--small${verdict === 'changed' ? ' secondlook__on' : ''}`} disabled={disabled} onClick={() => look.judge(currentImage, 'changed')}>
                {t('phrases.secondLook.changed')}
              </button>
            </>
          )}
          <button type="button" className="btn btn--small" onClick={look.stop}>
            {t('phrases.secondLook.end')}
          </button>
        </>
      ) : (
        <>
          <button type="button" className="btn btn--small" disabled={disabled} onClick={look.start} title={t('phrases.secondLook.startHint')}>
            {t('phrases.secondLook.title')}
          </button>
          {info && info.reviewed > 0 && <span className="trainer__dim">{t('phrases.secondLook.lastTime', { figure: figure(info.changed, info.reviewed, info.rate, translator) })}</span>}
        </>
      )}
      {look.error && <span className="run__warn" role="alert">{look.error}</span>}
    </div>
  );
}
