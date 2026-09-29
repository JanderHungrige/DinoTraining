/**
 * What the Dataset Generator runs with (docs 25, 27 and 42).
 *
 * A **discriminated union** rather than one object with half its fields null. An expert
 * head needs a backbone and an instance; a mask annotator needs a concept and an annotator
 * id, and neither set is meaningful to the other. A single flat shape would make every
 * reader check which half is populated.
 */

import type { ImageSource } from '../components/ImageSourceField';

export interface ExpertConfig {
  readonly kind: 'expert';
  readonly datasetId: string;
  readonly images: ImageSource;
  readonly backboneId: string;
  readonly instanceId: string;
  readonly scoreThreshold: number;
}

export interface MaskConfig {
  readonly kind: 'masks';
  readonly datasetId: string;
  readonly images: ImageSource;
  readonly annotatorId: string;
  readonly concept: string;
  readonly scoreThreshold: number;
}

export interface FoundationConfig {
  readonly kind: 'foundation';
  readonly datasetId: string;
  readonly images: ImageSource;
  /** Catalogue id of an installed detector. No backbone: it brings its own. */
  readonly foundationId: string;
  /** What to look for, when the chosen model is prompted (doc 66). Empty for RF-DETR,
   *  which ignores it. Not optional: a field that is sometimes absent is a field every
   *  caller has to remember, and the Studio already learned that with `concept`. */
  readonly concept: string;
  readonly scoreThreshold: number;
}

export type GeneratorConfig = ExpertConfig | MaskConfig | FoundationConfig;
