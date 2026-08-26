/**
 * Running whichever proposer the Dataset Generator was configured with.
 *
 * Extracted from `useGeneratorSession` when that crossed 300 lines, and it is the same seam
 * `lib/proposeFor.ts` took out of the Studio's hook: this is the one place that branches on
 * *what kind of model* a run uses, and everything around it is navigation and saving.
 *
 * Returns a result rather than setting state, so the hook keeps the one thing it must not
 * give away — the request ticket that stops a late response for an image the user has
 * already navigated past from landing on the one now on screen.
 */

import { foundationCanvasBoxes, proposeWithFoundation } from '../api/foundation';
import {
  proposeMasks,
  proposeWithExpertHead,
  toCanvasBoxes,
  toReviewMasks,
  type MaskProposalResponse,
} from '../api/generate';
import type { GeneratorConfig } from '../hooks/useGeneratorSession';
import type { CanvasBox, ReviewMask } from '../types/annotation';

export interface GeneratorProposal {
  readonly boxes: readonly CanvasBox[];
  readonly masks: readonly ReviewMask[];
  readonly width: number;
  readonly height: number;
  readonly producerName: string;
  readonly producerDetail: string;
  /** True when anything was proposed — what makes the run worth saving. */
  readonly found: boolean;
  /** The raw mask response, which the save path needs to re-encode RLE. Null for boxes. */
  readonly maskResponse: MaskProposalResponse | null;
}

export async function proposeForGenerator(
  config: GeneratorConfig,
  imagePath: string,
): Promise<GeneratorProposal> {
  if (config.kind === 'foundation') {
    const response = await proposeWithFoundation({
      imagePath,
      foundationId: config.foundationId,
      // Sent only when there is one. The API ignores it for an unprompted model, but an
      // empty string on the wire is indistinguishable from a prompt the user cleared.
      ...(config.concept ? { concept: config.concept } : {}),
      scoreThreshold: config.scoreThreshold,
    });
    return {
      boxes: foundationCanvasBoxes(response),
      masks: [],
      width: response.width,
      height: response.height,
      producerName: response.model_name,
      producerDetail: response.model_summary,
      found: response.boxes.length > 0,
      maskResponse: null,
    };
  }

  if (config.kind === 'expert') {
    const response = await proposeWithExpertHead({
      imagePath,
      backboneId: config.backboneId,
      instanceId: config.instanceId,
      scoreThreshold: config.scoreThreshold,
    });
    return {
      boxes: toCanvasBoxes(response),
      masks: [],
      width: response.width,
      height: response.height,
      producerName: response.head_name,
      producerDetail: response.head_summary,
      found: response.boxes.length > 0,
      maskResponse: null,
    };
  }

  const response = await proposeMasks({
    imagePath,
    concept: config.concept,
    annotatorId: config.annotatorId,
    threshold: config.scoreThreshold,
  });
  return {
    boxes: [],
    masks: toReviewMasks(response),
    width: response.width,
    height: response.height,
    producerName: response.annotator_name,
    producerDetail: `${response.masks.length} mask(s) for “${config.concept}”`,
    found: response.masks.length > 0,
    maskResponse: response,
  };
}
