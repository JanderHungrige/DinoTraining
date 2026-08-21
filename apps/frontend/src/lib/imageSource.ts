/**
 * Resolving "where the images come from" to an actual list (doc 50).
 *
 * One function, because three surfaces ask the same question and a copy in each is three
 * chances for a dataset source to behave subtly differently from a folder one — which is
 * precisely the difference the user should never be able to feel.
 */

import { listFolderImages } from '../api/annotate';
import { listDatasetImages } from '../api/datasets';
import type { ImageSource } from '../components/ImageSourceField';

export async function resolveImageSource(
  source: ImageSource,
  signal?: AbortSignal,
): Promise<string[]> {
  if (source.kind === 'dataset') {
    const entries = await listDatasetImages(source.datasetId, signal);
    return entries.map((entry) => entry.path);
  }
  return listFolderImages(source.folder, signal);
}

/** What to say when a source turns out to be empty, or unreadable. */
export function sourceNoun(source: ImageSource): string {
  return source.kind === 'dataset' ? 'dataset' : 'folder';
}

/** A stable key for a source, for effect dependencies. Two sources of different kinds
 *  must never compare equal, or switching between them would not reload. */
export function sourceKey(source: ImageSource | null): string {
  if (source === null) return '';
  return source.kind === 'dataset' ? `dataset:${source.datasetId}` : `folder:${source.folder}`;
}
