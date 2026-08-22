/**
 * Running whichever proposer a session was configured with (doc 50 refactor).
 *
 * Extracted from `useAnnotationSession` when that crossed 300 lines, and it is the right
 * seam: this is the one place that branches on *what kind of model* a session runs, and
 * everything around it is about navigation and saving.
 *
 * All three branches return proposals already in **source pixel coordinates** and already
 * carrying their own provenance, so nothing downstream branches on the mode again.
 */

import { proposeBoxes, toCanvasBoxes } from '../api/annotate';
import {
  proposeWithExpertHead,
  toCanvasBoxes as expertBoxes,
} from '../api/generate';
import { foundationCanvasBoxes, proposeWithFoundation } from '../api/foundation';
import type { ProposalSource } from '../hooks/useAnnotationSession';
import type { CanvasBox } from '../types/annotation';

export interface Proposed {
  readonly boxes: readonly CanvasBox[];
  readonly width: number;
  readonly height: number;
}

export async function proposeFor(
  source: ProposalSource,
  imagePath: string,
): Promise<Proposed> {
  if (source.kind === 'foundation') {
    const response = await proposeWithFoundation({
      imagePath,
      foundationId: source.foundationId,
      scoreThreshold: source.scoreThreshold,
      ...(source.concept ? { concept: source.concept } : {}),
    });
    return {
      boxes: foundationCanvasBoxes(response),
      width: response.width,
      height: response.height,
    };
  }

  if (source.kind === 'head') {
    const response = await proposeWithExpertHead({
      imagePath,
      backboneId: source.backboneId,
      instanceId: source.instanceId,
      scoreThreshold: source.scoreThreshold,
    });
    return { boxes: expertBoxes(response), width: response.width, height: response.height };
  }

  const response = await proposeBoxes({
    imagePath,
    prompt: source.prompt,
    boxThreshold: source.boxThreshold,
    textThreshold: source.textThreshold,
  });
  return { boxes: toCanvasBoxes(response), width: response.width, height: response.height };
}

/** What to say when a proposer fails, named by which one it was. */
export function proposalFailure(source: ProposalSource): string {
  if (source.kind === 'head') return 'Could not run that head.';
  if (source.kind === 'foundation') return 'Could not run that detector.';
  return 'Could not run the detector.';
}
