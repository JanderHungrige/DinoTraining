/**
 * Decoding a video into a dataset's frames (doc 73).
 *
 * Mirrors backend/app/api/v1/video_extract.py. A job, polled, because a few hundred frames
 * of 1080p take longer than a request should.
 */

import { apiFetch } from './client';
import type { RunState } from './video';

export interface ExtractedFrame {
  /** The frame's number in the video, counting from zero. */
  readonly index: number;
  readonly path: string;
}

export interface ExtractJob {
  readonly job_id: string;
  readonly state: RunState;
  readonly done: number;
  readonly total: number;
  readonly message: string;
  readonly frames: readonly ExtractedFrame[];
}

export interface ExtractRequest {
  readonly source: string;
  readonly datasetId: string;
  readonly start: number;
  readonly count: number;
  readonly stride: number;
}

function isExtractJob(value: unknown): value is ExtractJob {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as { job_id?: unknown }).job_id === 'string' &&
    Array.isArray((value as { frames?: unknown }).frames)
  );
}

export function startExtract(request: ExtractRequest, signal?: AbortSignal): Promise<ExtractJob> {
  return apiFetch('/video/extract', isExtractJob, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source: request.source,
      dataset_id: request.datasetId,
      start: request.start,
      count: request.count,
      stride: request.stride,
    }),
    ...(signal ? { signal } : {}),
  });
}

export function pollExtract(jobId: string, signal?: AbortSignal): Promise<ExtractJob> {
  return apiFetch(
    `/video/extract/${encodeURIComponent(jobId)}`,
    isExtractJob,
    signal ? { signal } : undefined,
  );
}

export function cancelExtract(jobId: string): Promise<ExtractJob> {
  return apiFetch(`/video/extract/${encodeURIComponent(jobId)}`, isExtractJob, {
    method: 'DELETE',
  });
}

/** Everything the loop in `extractFrames` reports while it waits. */
export type ExtractProgress = Pick<ExtractJob, 'done' | 'total'>;

/**
 * Starts an extraction and waits for it, reporting progress. Resolves with the frames in
 * video order; rejects with the job's own message when it fails. Aborting cancels the job
 * on the server too, so leaving the tab does not leave a decoder running.
 */
export async function extractFrames(
  request: ExtractRequest,
  onProgress: (progress: ExtractProgress) => void,
  signal: AbortSignal,
  pollMs = 400,
): Promise<readonly ExtractedFrame[]> {
  let job = await startExtract(request, signal);
  const cancel = (): void => void cancelExtract(job.job_id).catch(() => undefined);
  signal.addEventListener('abort', cancel, { once: true });
  try {
    while (job.state === 'pending' || job.state === 'running') {
      onProgress({ done: job.done, total: job.total });
      await new Promise((resolve) => setTimeout(resolve, pollMs));
      signal.throwIfAborted();
      job = await pollExtract(job.job_id, signal);
    }
  } finally {
    signal.removeEventListener('abort', cancel);
  }
  if (job.state === 'failed') throw new Error(job.message || 'The video could not be decoded.');
  onProgress({ done: job.done, total: job.total });
  return job.frames;
}
