/**
 * Playback slice of the API contract (doc 68).
 *
 * Mirrors backend/app/api/v1/video.py. A folder and a video file answer the same
 * questions, which is the point — nothing here branches on which one the user picked.
 */

import { apiFetch, apiUrl } from './client';
import type { Prediction } from './inference';

export interface SequenceInfo {
  readonly source: string;
  readonly kind: 'folder' | 'video';
  readonly frames: number;
  /** `null` for a folder, which has no frame rate of its own. */
  readonly fps: number | null;
  readonly duration: number | null;
  readonly width: number;
  readonly height: number;
}

export interface FramePredictions {
  readonly index: number;
  readonly predictions: readonly Prediction[];
}

export type RunState = 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';

export interface SequenceRun {
  readonly job_id: string;
  readonly state: RunState;
  readonly done: number;
  readonly total: number;
  readonly unreadable: number;
  readonly message: string;
  readonly start: number;
  readonly frames: readonly FramePredictions[];
}

export interface StartRunRequest {
  readonly source: string;
  readonly start: number;
  readonly count: number;
  readonly backboneId: string;
  readonly instanceIds: readonly string[];
  readonly foundationIds: readonly string[];
  readonly concept: string;
  readonly scoreThreshold: number;
}

/** When a folder has no frame rate of its own, this is what the player counts at. */
export const DEFAULT_FPS = 10;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isSequenceInfo(value: unknown): value is SequenceInfo {
  return isRecord(value) && typeof value['frames'] === 'number';
}

function isRun(value: unknown): value is SequenceRun {
  return isRecord(value) && typeof value['job_id'] === 'string';
}

export async function probeSequence(
  path: string,
  signal?: AbortSignal,
): Promise<SequenceInfo> {
  return apiFetch(
    `/video/probe?path=${encodeURIComponent(path)}`,
    isSequenceInfo,
    signal ? { signal } : undefined,
  );
}

/**
 * Where to fetch one frame's pixels.
 *
 * A URL rather than a fetch, so an `<img>` loads it and the browser's own cache does the
 * work — scrubbing backwards over a decoded video is otherwise a re-decode per frame.
 */
export function frameUrl(source: string, index: number): string {
  // `apiUrl`, not a second URL builder: that is how a stream ends up pointing at the wrong
  // port in a packaged build while every fetch keeps working.
  return apiUrl(`/video/frame?path=${encodeURIComponent(source)}&index=${index}`);
}

export async function startRun(
  request: StartRunRequest,
  signal?: AbortSignal,
): Promise<SequenceRun> {
  return apiFetch('/video/runs', isRun, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source: request.source,
      start: request.start,
      count: request.count,
      backbone_id: request.backboneId,
      instance_ids: request.instanceIds,
      foundation_ids: request.foundationIds,
      concept: request.concept,
      score_threshold: request.scoreThreshold,
    }),
    ...(signal ? { signal } : {}),
  });
}

/**
 * Progress, plus the frames in `[since, until)`.
 *
 * The window is not an optimisation detail: without it every poll re-sends every finished
 * frame, and a 500-frame run carrying masks re-sends megabytes the player already holds.
 */
export async function pollRun(
  jobId: string,
  since: number,
  until: number,
  signal?: AbortSignal,
): Promise<SequenceRun> {
  return apiFetch(
    `/video/runs/${jobId}?since=${since}&until=${until}`,
    isRun,
    signal ? { signal } : undefined,
  );
}

export async function cancelRun(jobId: string): Promise<SequenceRun> {
  return apiFetch(`/video/runs/${jobId}`, isRun, { method: 'DELETE' });
}

/**
 * Roughly how long a run will take, in seconds.
 *
 * Measured per-frame costs on this project's own hardware, not a guess: Grounded SAM and
 * SAM 3 chain two large models, RF-DETR and Grounding DINO are single passes, and a DINOv2
 * head shares one backbone pass with every other head selected.
 *
 * An estimate, and the UI labels it as one. It is worth showing precisely because it is
 * the number that changes the decision — someone who sees four minutes picks a shorter
 * range rather than cancelling three minutes in.
 */
export function estimateSeconds(
  frames: number,
  foundationIds: readonly string[],
  headCount: number,
): number {
  const perFoundation = foundationIds.reduce((total, id) => {
    if (id.startsWith('grounded-sam') || id === 'sam3') return total + 5;
    if (id.startsWith('grounding-dino')) return total + 0.6;
    if (id.startsWith('depth-anything')) return total + 0.4;
    return total + 0.15;
  }, 0);
  // Heads share one backbone pass, so N heads is not N times the cost.
  const perHeads = headCount > 0 ? 0.2 + 0.02 * (headCount - 1) : 0;
  return frames * (perFoundation + perHeads);
}

/** The estimate as something readable — "about 4 min", not "241.7s". */
export function describeEstimate(seconds: number): string {
  if (seconds < 1) return 'a moment';
  if (seconds < 90) return `about ${Math.round(seconds)} sec`;
  if (seconds < 3600) return `about ${Math.round(seconds / 60)} min`;
  return `about ${(seconds / 3600).toFixed(1)} hours`;
}
