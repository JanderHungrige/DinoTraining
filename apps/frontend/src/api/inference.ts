/** Inference slice of the API contract. Mirrors backend/app/api/v1/inference.py. */

import { apiFetch } from './client';

export interface SourceItem {
  /** Stable, opaque identity — never a path. Key results and list entries on this. */
  readonly item_id: string;
  readonly name: string;
  /** Absolute path, for image bytes and for `POST /inference`'s `image_path`. */
  readonly path: string;
}

export interface ImageSource {
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

function isImageSource(value: unknown): value is ImageSource {
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
export function resolveSource(path: string, signal?: AbortSignal): Promise<ImageSource> {
  return apiFetch(
    `/inference/source?path=${encodeURIComponent(path)}`,
    isImageSource,
    signal ? { signal } : undefined,
  );
}
