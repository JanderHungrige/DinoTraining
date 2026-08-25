/**
 * Foundation-model slice of the API contract. Mirrors backend/app/api/v1/foundation.py.
 *
 * A foundation model predicts on its own — no backbone, no head, no shared pass. It still
 * returns a `Prediction`, which is what lets the viewer put it in a pane beside a trained
 * head and the overlay registry draw it without knowing the difference.
 */

import { apiFetch } from './client';
import { isPrediction, type Prediction } from './inference';
import type { CanvasBox, CanvasMask } from '../types/annotation';

export interface FoundationInfo {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly task: string;
  readonly render_hint: string;
  readonly model_id: string;
  readonly licence: string;
  /** Shown in the viewer as well as the admin panel — this is where the output is used. */
  readonly non_commercial: boolean;
  readonly installed: boolean;
  readonly approx_size_mb: number;
  /** True when the model needs a text concept before it predicts anything (doc 45).
   *  Grounded SAM segments whatever you name; RF-DETR ignores whatever you type. */
  readonly takes_concept: boolean;
}

/** Can this model's output be reviewed as boxes?
 *
 *  `render_hint` alone stopped answering this at doc 45. A concept segmenter reports
 *  `masks` — that is what the viewer draws — but Grounding DINO found boxes on the way
 *  there, so the Studio can review them. Depth still cannot be, and that is the whole
 *  point of keeping the rule in one exported place rather than inline in two pickers. */
export function proposesBoxes(entry: FoundationInfo): boolean {
  return entry.render_hint === 'boxes' || entry.takes_concept;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isFoundation(value: unknown): value is FoundationInfo {
  if (!isRecord(value)) return false;
  return (
    typeof value['id'] === 'string' &&
    typeof value['title'] === 'string' &&
    typeof value['installed'] === 'boolean' &&
    typeof value['non_commercial'] === 'boolean'
  );
}

function isFoundationList(value: unknown): value is { foundations: FoundationInfo[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['foundations']) &&
    value['foundations'].every(isFoundation)
  );
}

export async function listFoundations(signal?: AbortSignal): Promise<FoundationInfo[]> {
  const body = await apiFetch(
    '/foundation',
    isFoundationList,
    signal ? { signal } : undefined,
  );
  return body.foundations;
}

export interface RunFoundationOptions {
  readonly imagePath: string;
  readonly foundationId: string;
  /** Ignored by every model whose `takes_concept` is false. */
  readonly concept?: string;
}

export function runFoundation(
  options: RunFoundationOptions,
  signal?: AbortSignal,
): Promise<Prediction> {
  return apiFetch('/foundation/predict', isPrediction, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      foundation_id: options.foundationId,
      ...(options.concept ? { concept: options.concept } : {}),
    }),
    ...(signal ? { signal } : {}),
  });
}

// --- proposals (doc 42) -------------------------------------------------------------
//
// Deliberately the same shape the expert route returns, because the review surface should
// consume one shape rather than learn which kind of model produced a box.

/** One proposal: the box, and the segmentation behind it when the model produced one. */
export interface ProposedBoxDto {
  readonly box: {
    readonly label: CanvasBox['label'];
    readonly provenance: CanvasBox['provenance'];
    readonly x: number;
    readonly y: number;
    readonly w: number;
    readonly h: number;
    readonly score: number | null;
    readonly prompt: string | null;
    readonly producer: CanvasBox['producer'] | null;
  };
  /** Null for a detector — RF-DETR has no segmentation to offer (doc 61). */
  readonly mask: { readonly rle: CanvasMask['rle']; readonly png: string } | null;
}

export interface FoundationProposalResponse {
  readonly image_path: string;
  readonly width: number;
  readonly height: number;
  readonly device: string;
  readonly model_name: string;
  readonly model_summary: string;
  /** Still `boxes`, still one entry per annotation. The mask lives *inside* an entry
   *  rather than in a parallel list, because a parallel list is paired by index and index
   *  pairing breaks the moment a reviewer removes one. */
  readonly boxes: readonly ProposedBoxDto[];
}

function isFoundationProposal(value: unknown): value is FoundationProposalResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value['width'] === 'number' &&
    typeof value['height'] === 'number' &&
    typeof value['model_name'] === 'string' &&
    Array.isArray(value['boxes'])
  );
}

export interface ProposeFoundationOptions {
  readonly imagePath: string;
  readonly foundationId: string;
  readonly scoreThreshold?: number;
  /** Required by a concept segmenter; the backend refuses an empty one rather than
   *  returning nothing, because nothing-found and nothing-asked look identical. */
  readonly concept?: string;
}

export function proposeWithFoundation(
  options: ProposeFoundationOptions,
  signal?: AbortSignal,
): Promise<FoundationProposalResponse> {
  return apiFetch('/generate/foundation', isFoundationProposal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      foundation_id: options.foundationId,
      ...(options.scoreThreshold !== undefined
        ? { score_threshold: options.scoreThreshold }
        : {}),
      ...(options.concept ? { concept: options.concept } : {}),
    }),
    ...(signal ? { signal } : {}),
  });
}

/** Same mapping the expert route gets: the class rides as `text` and is renamed to
 *  `prompt` on save (doc 31). The mask rides along untouched when there is one (doc 61). */
export function foundationCanvasBoxes(
  response: FoundationProposalResponse,
): CanvasBox[] {
  return response.boxes.map((entry, index) => ({
    id: `foundation-${index}`,
    label: entry.box.label,
    provenance: entry.box.provenance,
    x: entry.box.x,
    y: entry.box.y,
    w: entry.box.w,
    h: entry.box.h,
    ...(entry.box.score !== null ? { score: entry.box.score } : {}),
    ...(entry.box.prompt ? { text: entry.box.prompt } : {}),
    ...(entry.box.producer ? { producer: entry.box.producer } : {}),
    ...(entry.mask ? { mask: { rle: entry.mask.rle, png: entry.mask.png } } : {}),
  }));
}

// --- fine-tuning (doc 44) ------------------------------------------------------------

export interface FinetuneEpoch {
  readonly epoch: number;
  readonly train_loss: number;
  readonly metrics: Record<string, number>;
}

export interface FinetuneJob {
  readonly job_id: string;
  readonly state: 'pending' | 'running' | 'complete' | 'failed' | 'cancelled';
  readonly epoch: number;
  readonly total_epochs: number;
  readonly best_metric: number | null;
  readonly class_names: readonly string[];
  /** Proof the backbone was actually frozen — a silent no-op looks like a slow success. */
  readonly frozen_parameters: number;
  readonly trainable_parameters: number;
  readonly message: string;
  readonly instance_id: string | null;
  readonly history: readonly FinetuneEpoch[];
}

function isFinetuneJob(value: unknown): value is FinetuneJob {
  if (!isRecord(value)) return false;
  return (
    typeof value['job_id'] === 'string' &&
    typeof value['state'] === 'string' &&
    typeof value['total_epochs'] === 'number' &&
    Array.isArray(value['history'])
  );
}

export interface StartFinetuneOptions {
  readonly foundationId: string;
  readonly datasetIds: readonly string[];
  readonly name: string;
  readonly epochs: number;
  readonly learningRate: number;
  /** Backbone blocks to train alongside the decoder (doc 55). 0 frozen, -1 all.
   *  Safe on this path and refused for heads: the fine-tune saves the whole model. */
  readonly unfreezeBlocks?: number;
}

export function startFinetune(options: StartFinetuneOptions): Promise<FinetuneJob> {
  return apiFetch('/foundation/finetune', isFinetuneJob, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      foundation_id: options.foundationId,
      dataset_ids: options.datasetIds,
      name: options.name,
      epochs: options.epochs,
      learning_rate: options.learningRate,
      ...(options.unfreezeBlocks === undefined
        ? {}
        : { unfreeze_blocks: options.unfreezeBlocks }),
    }),
  });
}

export function readFinetune(jobId: string, signal?: AbortSignal): Promise<FinetuneJob> {
  return apiFetch(
    `/foundation/finetune/${encodeURIComponent(jobId)}`,
    isFinetuneJob,
    signal ? { signal } : undefined,
  );
}

export function cancelFinetune(jobId: string): Promise<FinetuneJob> {
  return apiFetch(`/foundation/finetune/${encodeURIComponent(jobId)}/cancel`, isFinetuneJob, {
    method: 'POST',
  });
}



/** Delete a fine-tuned model (doc 51).
 *
 *  Only an instance, never a catalogue entry — those are downloads managed in Admin /
 *  Models, and the backend answers 404 for one rather than pretending to remove it. */
export async function deleteFoundationInstance(
  instanceId: string,
  signal?: AbortSignal,
): Promise<void> {
  await apiFetch(
    `/foundation/instances/${encodeURIComponent(instanceId)}`,
    (value): value is unknown => value !== undefined,
    { method: 'DELETE', ...(signal ? { signal } : {}) },
  );
}
