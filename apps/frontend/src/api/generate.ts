/**
 * Dataset Generator slice of the API contract.
 * Mirrors backend/app/api/v1/generate.py.
 *
 * Proposals come back in the same shape the Annotation Studio's do, on purpose: the
 * generator reviews boxes with the same canvas, and a second subtly-different payload for
 * the same job is how two review surfaces drift apart.
 */

import { apiFetch } from './client';
import type { CanvasBox, Label, Provenance } from '../types/annotation';

export interface ExpertProposalResponse {
  readonly image_path: string;
  readonly width: number;
  readonly height: number;
  readonly device: string;
  /** The user's own label for the head. */
  readonly head_name: string;
  /** What the head does — rendered, never rebuilt. Doc 12's cross-tab contract. */
  readonly head_summary: string;
  readonly boxes: readonly {
    readonly label: Label;
    readonly provenance: Provenance;
    readonly x: number;
    readonly y: number;
    readonly w: number;
    readonly h: number;
    readonly prompt: string | null;
    readonly score: number | null;
  }[];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isExpertProposal(value: unknown): value is ExpertProposalResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value['image_path'] === 'string' &&
    typeof value['width'] === 'number' &&
    typeof value['height'] === 'number' &&
    typeof value['head_summary'] === 'string' &&
    Array.isArray(value['boxes'])
  );
}

export interface ExpertProposalRequest {
  readonly imagePath: string;
  readonly backboneId: string;
  readonly instanceId: string;
  readonly scoreThreshold: number;
}

export async function proposeWithExpertHead(
  request: ExpertProposalRequest,
  signal?: AbortSignal,
): Promise<ExpertProposalResponse> {
  return apiFetch('/generate/expert', isExpertProposal, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: request.imagePath,
      backbone_id: request.backboneId,
      instance_id: request.instanceId,
      score_threshold: request.scoreThreshold,
    }),
    ...(signal ? { signal } : {}),
  });
}

/** Proposals to canvas boxes. Ids are client-side only; coordinates are already natural. */
export function toCanvasBoxes(response: ExpertProposalResponse): CanvasBox[] {
  return response.boxes.map((box, index) => ({
    id: `expert-${index}`,
    label: box.label,
    provenance: box.provenance,
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    ...(box.score !== null ? { score: box.score } : {}),
    ...(box.prompt ? { text: box.prompt } : {}),
  }));
}
