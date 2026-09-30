/**
 * Opening one tab *at* something (doc 74): the Generator's "Inspect what I just annotated"
 * is the first navigation in the app that carries a payload.
 *
 * `nonce` makes the same request twice a new request: inspecting dataset A, wandering off
 * to another dataset, and pressing the button again must jump back to A.
 */

export interface InspectRequest {
  readonly datasetId: string;
  /** The video or folder to open, when the caller knows it. */
  readonly sequence: string | null;
  readonly nonce: number;
}

/** Doc 90: open Training at a dataset with a preparation recipe chosen. */
export interface TrainRequest {
  readonly datasetId: string;
  readonly recipeId: string;
  readonly nonce: number;
}
