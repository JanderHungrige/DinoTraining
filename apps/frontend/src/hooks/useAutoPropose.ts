/**
 * Propose as soon as an image arrives, when the user has asked for that (doc 70).
 *
 * Once per arrival, and never for an image this session has already saved: going back to a
 * saved image shows what was saved, and a fresh proposal would silently replace the user's
 * corrections, which auto-save would then write over them. A failure is not retried either,
 * because a proposer that errors must not be called in a loop. The ref also absorbs
 * StrictMode's double effect, which would otherwise start two five-second SAM runs.
 */

import { useEffect, useRef } from 'react';

import type { ImageReview } from '../lib/generatorSave';

export interface AutoProposeTarget {
  readonly currentImage: string | null;
  readonly proposing: boolean;
  readonly propose: () => Promise<ImageReview | null>;
  readonly saved: (path: string) => ImageReview | undefined;
  /** The image the review on screen was proposed for (doc 71). */
  readonly proposedFor: string | null;
}

export function useAutoPropose(session: AutoProposeTarget, enabled: boolean): void {
  const askedFor = useRef<string | null>(null);
  const { currentImage, proposing, propose, saved, proposedFor } = session;

  useEffect(() => {
    if (!enabled || currentImage === null || proposing) return;
    if (askedFor.current === currentImage) return;
    if (saved(currentImage) !== undefined) return;
    // Already has a proposal on screen, e.g. autoplay was stopped during its hold. That
    // proposal is what the user stopped to correct; replacing it would lose the reason.
    if (proposedFor === currentImage) return;
    askedFor.current = currentImage;
    void propose();
  }, [enabled, currentImage, proposing, propose, saved, proposedFor]);
}
