/**
 * What the Dataset Generator's session offers its tab (docs 26, 70 and 71).
 */

import type { DatasetCounts } from '../api/datasets';
import type { ImageReview } from '../lib/generatorSave';
import type { CanvasBox, ReviewMask } from './annotation';

export interface MoveOptions {
  readonly autoSave?: boolean;
}

export interface GeneratorSession {
  readonly images: readonly string[];
  /** Every image the source holds, ignoring any prescan filter. */
  readonly allImages: readonly string[];
  readonly filtered: boolean;
  readonly setFilter: (paths: readonly string[] | null) => void;
  readonly index: number;
  readonly currentImage: string | null;
  readonly boxes: readonly CanvasBox[];
  readonly masks: readonly ReviewMask[];
  readonly imageSize: { width: number; height: number } | null;
  /** What produced the current proposals — a head's name, or an annotator's. */
  readonly producerName: string | null;
  readonly producerDetail: string | null;
  readonly loading: boolean;
  readonly proposing: boolean;
  readonly saving: boolean;
  /** True when there is something reviewed that has not been written yet. */
  readonly dirty: boolean;
  readonly counts: DatasetCounts;
  readonly error: string | null;
  readonly setBoxes: (boxes: CanvasBox[]) => void;
  readonly setMasks: (masks: ReviewMask[]) => void;
  readonly reportImageSize: (width: number, height: number) => void;
  /** Resolves to what was proposed, or null when it failed or the image changed meanwhile. */
  readonly propose: () => Promise<ImageReview | null>;
  /** Saves the given review, or the one on screen. False when the save failed. */
  readonly save: (review?: ImageReview) => Promise<boolean>;
  /** Moves on, saving a dirty image first when asked. False when that save failed and the
   *  session stayed where it was, so the review is not lost. */
  readonly next: (options?: MoveOptions) => Promise<boolean>;
  readonly previous: (options?: MoveOptions) => Promise<boolean>;
  /** What this session saved for an image, if anything. */
  readonly saved: (path: string) => ImageReview | undefined;
  readonly goTo: (index: number) => void;
  readonly show: (review: ImageReview) => void;
  /** The image the review on screen was proposed for, if any. */
  readonly proposedFor: string | null;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
}
