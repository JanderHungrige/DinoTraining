/**
 * A dataset as sequences to play back (docs 74, 75).
 *
 * Mirrors GET /datasets/{id}/sequences in backend/app/api/v1/dataset_images.py.
 */

import { apiFetch } from './client';

export interface SequenceFrame {
  /** The frame's number in its source: a video's frame, or a folder's sorted position. */
  readonly index: number;
  readonly path: string;
  /** False for a frame on disk that was never saved, because nothing was found there. */
  readonly annotated: boolean;
  /** Classes with a positive box or mask on this frame. */
  readonly classes: readonly string[];
}

export interface DatasetSequence {
  readonly source: string;
  readonly kind: 'video' | 'folder';
  readonly frames: readonly SequenceFrame[];
}

export interface DatasetSequences {
  readonly dataset_id: string;
  /** Every class in the dataset, sorted: the index is the colour, the same everywhere. */
  readonly class_names: readonly string[];
  readonly sequences: readonly DatasetSequence[];
  readonly loose: readonly SequenceFrame[];
}

function isSequences(value: unknown): value is DatasetSequences {
  return (
    typeof value === 'object' &&
    value !== null &&
    Array.isArray((value as { sequences?: unknown }).sequences) &&
    Array.isArray((value as { loose?: unknown }).loose) &&
    Array.isArray((value as { class_names?: unknown }).class_names)
  );
}

export function listDatasetSequences(
  datasetId: string,
  signal?: AbortSignal,
): Promise<DatasetSequences> {
  return apiFetch(
    `/datasets/${encodeURIComponent(datasetId)}/sequences`,
    isSequences,
    signal ? { signal } : undefined,
  );
}

/** "ride.mp4 · 300 frames", for a picker. */
export function sequenceLabel(sequence: DatasetSequence): string {
  const name = sequence.source.split(/[\\/]/).filter(Boolean).pop() ?? sequence.source;
  const annotated = sequence.frames.filter((frame) => frame.annotated).length;
  return `${name} · ${sequence.frames.length} frames, ${annotated} annotated`;
}
