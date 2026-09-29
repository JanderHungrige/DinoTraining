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
  if (source.kind === 'video') {
    // A video has no images until it is decoded into a dataset, which only the Generator
    // does (doc 73). Reaching here is a surface offering video that should not.
    throw new Error(VIDEO_NEEDS_DECODING);
  }
  return listFolderImages(source.folder, signal);
}

export const VIDEO_NEEDS_DECODING =
  'A video is decoded into frames first, and only the Dataset Generator does that.';

/** What to say when a source turns out to be empty, or unreadable. */
export function sourceNoun(source: ImageSource): string {
  return source.kind;
}

/** A stable key for a source, for effect dependencies. Two sources of different kinds
 *  must never compare equal, or switching between them would not reload. */
export function sourceKey(source: ImageSource | null): string {
  if (source === null) return '';
  switch (source.kind) {
    case 'dataset':
      return `dataset:${source.datasetId}`;
    case 'folder':
      return `folder:${source.folder}`;
    case 'video': {
      const { start, count, stride } = source.range;
      return `video:${source.path}:${start}:${count}:${stride}`;
    }
  }
}

const VIDEO_SUFFIXES = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'];

/** The containers the backend decodes (decode.py's VIDEO_SUFFIXES). */
export function looksLikeVideo(path: string): boolean {
  const lower = path.trim().toLowerCase();
  return VIDEO_SUFFIXES.some((suffix) => lower.endsWith(suffix));
}

/** Whether a source names something that can be listed or decoded. */
export function sourceReady(source: ImageSource): boolean {
  switch (source.kind) {
    case 'dataset':
      return source.datasetId !== '';
    case 'folder':
      return source.folder.trim() !== '';
    case 'video': {
      const { start, count, stride } = source.range;
      return looksLikeVideo(source.path) && start >= 0 && count >= 1 && stride >= 1;
    }
  }
}
