/** "Reviewing for m10 — picture 3 of 20" (doc 119), with "No m10 here →" and End review. */

import type { JSX } from 'react';

import type { Review } from '../hooks/useReview';
import { useT } from '../i18n';
import { phraseKey } from '../lib/phraseEdit';
import type { CanvasBox } from '../types/annotation';

export interface ReviewBannerProps {
  readonly review: Review;
  readonly position: number;
  readonly boxes: readonly CanvasBox[];
  readonly busy: boolean;
}

export function ReviewBanner({ review, position, boxes, busy }: ReviewBannerProps): JSX.Element | null {
  const { t } = useT();
  const name = review.className;
  if (name === null) return null;
  // A picture with an annotation of the class cannot be "no m10 here".
  const hasIt = boxes.some((box) => box.label !== 'negative' && phraseKey(box.text ?? '') === phraseKey(name));
  return (
    <section className="newclass__ask" aria-label={t('studio.review.label', { name })}>
      <p>
        <strong>{t('studio.review.title', { name, position, total: review.total })}</strong>{' '}
        {t('studio.review.hint', { name })}
      </p>
      <button type="button" className="btn btn--small" disabled={busy || hasIt} onClick={() => void review.notHere()}>
        {t('studio.review.notHere', { name })}
      </button>
      <button type="button" className="btn btn--small" onClick={review.end}>
        {t('studio.review.end')}
      </button>
      {review.error && <span className="run__warn" role="alert">{review.error}</span>}
    </section>
  );
}
