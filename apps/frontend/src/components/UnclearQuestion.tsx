/**
 * Autoplay has stopped to ask (doc 72). Focus moves to Continue when the question appears:
 * a run that pauses by itself has to be announced, or a keyboard or screen-reader user
 * would sit waiting on a run that is waiting on them.
 */

import { useEffect, useRef, type JSX } from 'react';

import { useT } from '../i18n';
import type { UnclearBand } from '../lib/unclearBand';

export interface UnclearQuestionProps {
  readonly imageNumber: number;
  readonly imageTotal: number;
  readonly count: number;
  readonly band: UnclearBand;
  readonly onContinue: () => void;
  readonly onStop: () => void;
}

export function UnclearQuestion({
  imageNumber,
  imageTotal,
  count,
  band,
  onContinue,
  onStop,
}: UnclearQuestionProps): JSX.Element {
  const { t, tp } = useT();
  const continueButton = useRef<HTMLButtonElement | null>(null);
  useEffect(() => continueButton.current?.focus(), [imageNumber]);

  // `{unclear}` is left unfilled and split on, so the word can be set in italics wherever
  // the language puts it.
  const [before, after = ''] = tp('generator.unclear.scored', count, {
    low: band.low.toFixed(2),
    high: band.high.toFixed(2),
  }).split('{unclear}');
  return (
    <section className="unclearq" role="alert" aria-label={t('generator.unclear.waitingAria')}>
      <p className="unclearq__text">
        <strong>{t('generator.unclear.paused', { number: imageNumber, total: imageTotal })}</strong>{' '}
        {before}
        <em>{t('generator.unclear.word')}</em>
        {after}
      </p>
      <div className="unclearq__actions">
        <button
          ref={continueButton}
          type="button"
          className="btn btn--primary"
          onClick={onContinue}
        >
          {t('generator.unclear.continue')}
        </button>
        <button type="button" className="btn" onClick={onStop}>
          {t('generator.unclear.stopHere')}
        </button>
      </div>
    </section>
  );
}
