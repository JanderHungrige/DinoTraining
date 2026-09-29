/**
 * Writing one reviewed image back to the dataset (docs 29 and 70).
 *
 * The review is passed in explicitly, never read from React state. Autoplay (doc 71) saves
 * what it has just proposed, and state set a moment earlier has not been rendered yet: a
 * `save()` reading state would write the *previous* image's boxes under this image's path.
 */

import {
  saveImageBoxes,
  saveImageMasks,
  type DatasetCounts,
  type FramePosition,
} from '../api/datasets';
import type { MaskProposalResponse } from '../api/generate';
import type { GeneratorConfig } from '../hooks/useGeneratorSession';
import type { CanvasBox, ReviewMask } from '../types/annotation';

/** Everything needed to show an image's review again, or to save it. */
export interface ImageReview {
  readonly path: string;
  readonly boxes: readonly CanvasBox[];
  readonly masks: readonly ReviewMask[];
  /** The raw mask proposal; the save path re-encodes the RLE from it. Null for boxes. */
  readonly maskResponse: MaskProposalResponse | null;
  readonly imageSize: { readonly width: number; readonly height: number } | null;
}

/** `frame` records where the image sits in its video or folder (doc 73); null for none. */
export async function saveReview(
  config: GeneratorConfig,
  review: ImageReview,
  frame: FramePosition | null = null,
): Promise<DatasetCounts> {
  if (config.kind === 'masks') {
    if (!review.maskResponse) {
      // Reachable by saving before anything was proposed. Refusing beats inventing an
      // empty proposal, which would wipe whatever the image already had stored.
      throw new Error('Propose masks before saving.');
    }
    return saveImageMasks(config.datasetId, review.maskResponse, review.masks, frame);
  }
  if (!review.imageSize) {
    throw new Error('The image has not loaded yet, so its boxes cannot be placed.');
  }
  return saveImageBoxes(
    config.datasetId,
    { path: review.path, width: review.imageSize.width, height: review.imageSize.height },
    review.boxes,
    frame,
  );
}
