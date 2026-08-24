/** Inference slice of the API contract. Mirrors backend/app/api/v1/inference.py. */

import { apiFetch } from './client';

export interface SourceItem {
  /** Stable, opaque identity — never a path. Key results and list entries on this. */
  readonly item_id: string;
  readonly name: string;
  /** Absolute path, for image bytes and for `POST /inference`'s `image_path`. */
  readonly path: string;
}

/** One path resolved to a browsable listing — a single image, or a folder's contents.
 *
 *  Named for what it *is* rather than for what was asked, because `ImageSource` now means
 *  the user's *choice* of where images come from (doc 50) and two types called the same
 *  thing in one codebase is a trap. */
export interface ResolvedSource {
  readonly kind: 'file' | 'folder';
  readonly root: string;
  readonly items: readonly SourceItem[];
  /** True when the folder held more than the backend's cap. */
  readonly truncated: boolean;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isSourceItem(value: unknown): value is SourceItem {
  return (
    isRecord(value) &&
    typeof value['item_id'] === 'string' &&
    typeof value['name'] === 'string' &&
    typeof value['path'] === 'string'
  );
}

function isResolvedSource(value: unknown): value is ResolvedSource {
  if (!isRecord(value)) return false;
  return (
    (value['kind'] === 'file' || value['kind'] === 'folder') &&
    typeof value['root'] === 'string' &&
    typeof value['truncated'] === 'boolean' &&
    Array.isArray(value['items']) &&
    value['items'].every(isSourceItem)
  );
}

/**
 * `GET /api/v1/inference/source` — resolve a path into the images to step through.
 *
 * A single image and a folder come back as the same shape. An empty folder is a success
 * with no items, not an error.
 */
export function resolveSource(path: string, signal?: AbortSignal): Promise<ResolvedSource> {
  return apiFetch(
    `/inference/source?path=${encodeURIComponent(path)}`,
    isResolvedSource,
    signal ? { signal } : undefined,
  );
}

/**
 * What the renderer dispatches on — never a task string it re-derives.
 *
 * Mirrors `RenderHint` in `app/ml/heads/registry.py`. Adding a head type to the backend
 * registry means adding a renderer here, and nothing else in the UI changes.
 */
export type RenderHint = 'labels' | 'boxes' | 'masks' | 'depth-map';

/** `[x, y, w, h]` in absolute source-image pixels, top-left origin. */
export type BoxTuple = readonly [number, number, number, number];

export interface LabelsPayload {
  readonly scores: readonly number[];
}

export interface BoxesPayload {
  readonly boxes: readonly BoxTuple[];
  readonly scores: readonly number[];
  readonly classes: readonly number[];
}

/**
 * Dense maps arrive as a base64 PNG, not as nested JSON arrays.
 *
 * A 3000x2000 segmentation is 18.5 MB of JSON numbers and 17 KB as a PNG — the map is
 * upsampled from a 32x32 patch grid, so the numbers are almost all redundant and PNG's
 * filtering removes exactly that redundancy. Drawing it is also less work than building
 * ImageData from arrays.
 */
export interface MasksPayload {
  /** Base64 PNG; each pixel's value *is* the class index. No palette — the client colours it. */
  readonly mask_png: string;
  readonly present_classes: readonly number[];
  readonly height: number;
  readonly width: number;
}

export interface DepthPayload {
  /** Base64 PNG; 0..255 normalised across `min`..`max`, so a pixel maps back to metres. */
  readonly depth_png: string;
  readonly min: number;
  readonly max: number;
  readonly height: number;
  readonly width: number;
}

export interface Prediction {
  readonly instance_id: string;
  /** Provenance-bearing name. Never a filename — doc 12's cross-tab contract. */
  readonly head_name: string;
  readonly head_type_id: string;
  readonly task: string;
  readonly render_hint: RenderHint;
  readonly class_names: readonly string[];
  readonly payload: Record<string, unknown>;
  readonly grid: readonly number[];
  readonly elapsed_ms: number;
}

export interface ComposedResult {
  readonly predictions: readonly Prediction[];
  /** Backbone forward passes actually run — two framings collapse seven head types. */
  readonly passes: number;
  readonly elapsed_ms: number;
}

const RENDER_HINTS: readonly string[] = ['labels', 'boxes', 'masks', 'depth-map'];

/** Exported so the foundation slice validates a prediction with the same guard.
 *  Both endpoints return this shape by design — a second copy would be free to drift. */
export function isPrediction(value: unknown): value is Prediction {
  if (!isRecord(value)) return false;
  return (
    typeof value['instance_id'] === 'string' &&
    typeof value['head_name'] === 'string' &&
    typeof value['render_hint'] === 'string' &&
    RENDER_HINTS.includes(value['render_hint']) &&
    Array.isArray(value['class_names']) &&
    isRecord(value['payload'])
  );
}

function isComposedResult(value: unknown): value is ComposedResult {
  if (!isRecord(value)) return false;
  return (
    typeof value['passes'] === 'number' &&
    typeof value['elapsed_ms'] === 'number' &&
    Array.isArray(value['predictions']) &&
    value['predictions'].every(isPrediction)
  );
}

export interface RunHeadsOptions {
  readonly imagePath: string;
  readonly backboneId: string;
  readonly instanceIds: readonly string[];
  readonly scoreThreshold?: number;
}

/** `POST /api/v1/inference/compose` — N heads over one image, sharing backbone passes. */
export function runHeads(
  options: RunHeadsOptions,
  signal?: AbortSignal,
): Promise<ComposedResult> {
  return apiFetch('/inference/compose', isComposedResult, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      backbone_id: options.backboneId,
      instance_ids: options.instanceIds,
      ...(options.scoreThreshold === undefined
        ? {}
        : { score_threshold: options.scoreThreshold }),
    }),
    ...(signal ? { signal } : {}),
  });
}
