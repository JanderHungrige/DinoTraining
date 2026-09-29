/**
 * Autoplay has stopped to ask (doc 72). Focus moves to Continue when the question appears:
 * a run that pauses by itself has to be announced, or a keyboard or screen-reader user
 * would sit waiting on a run that is waiting on them.
 */

import { useEffect, useRef, type JSX } from 'react';

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
  const continueButton = useRef<HTMLButtonElement | null>(null);
  useEffect(() => continueButton.current?.focus(), [imageNumber]);

  const noun = count === 1 ? 'proposal scored' : 'proposals scored';
  return (
    <section className="unclearq" role="alert" aria-label="Autoplay is waiting for you">
      <p className="unclearq__text">
        <strong>
          Paused on image {imageNumber} of {imageTotal}.
        </strong>{' '}
        {count} {noun} between {band.low.toFixed(2)} and {band.high.toFixed(2)} and{' '}
        {count === 1 ? 'is' : 'are'} marked <em>unclear</em>. Click a box to cycle its label (or focus it and press
        1 positive · 2 negative · 3 unclear), then continue. Left as it is, it saves as unclear.
      </p>
      <div className="unclearq__actions">
        <button
          ref={continueButton}
          type="button"
          className="btn btn--primary"
          onClick={onContinue}
        >
          Continue
        </button>
        <button type="button" className="btn" onClick={onStop}>
          Stop here
        </button>
      </div>
    </section>
  );
}
