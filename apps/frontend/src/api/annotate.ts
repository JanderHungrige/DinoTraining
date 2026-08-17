/** Annotate slice of the API contract. Mirrors backend/app/api/v1/annotate.py. */

import { API_BASE_URL, API_PREFIX, apiFetch } from './client';
import type { CanvasBox, Label, Provenance } from '../types/annotation';

export interface ProposalResponse {
  readonly image_path: string;
  readonly width: number;
  readonly height: number;
  readonly prompt: string;
  readonly device: string;
  readonly boxes: readonly {
    readonly label: Label;
    readonly provenance: Provenance;
    readonly x: number;
    readonly y: number;
    readonly w: number;
    readonly h: number;
    readonly score?: number;
    readonly text?: string;
  }[];
}

export const DEFAULT_BOX_THRESHOLD = 0.3;
export const DEFAULT_TEXT_THRESHOLD = 0.25;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isProposalResponse(value: unknown): value is ProposalResponse {
  if (!isRecord(value)) return false;
  return (
    typeof value['image_path'] === 'string' &&
    typeof value['width'] === 'number' &&
    typeof value['height'] === 'number' &&
    Array.isArray(value['boxes'])
  );
}

function isFolderListing(value: unknown): value is { folder: string; images: string[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['images']) &&
    value['images'].every((entry) => typeof entry === 'string')
  );
}

export async function listFolderImages(folder: string, signal?: AbortSignal): Promise<string[]> {
  const body = await apiFetch(
    `/annotate/folder?path=${encodeURIComponent(folder)}`,
    isFolderListing,
    signal ? { signal } : undefined,
  );
  return body.images;
}

export interface ProposeOptions {
  readonly imagePath: string;
  readonly prompt: string;
  readonly boxThreshold?: number;
  readonly textThreshold?: number;
  readonly modelId?: string;
}

export function proposeBoxes(
  options: ProposeOptions,
  signal?: AbortSignal,
): Promise<ProposalResponse> {
  return apiFetch('/annotate', isProposalResponse, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: options.imagePath,
      prompt: options.prompt,
      box_threshold: options.boxThreshold ?? DEFAULT_BOX_THRESHOLD,
      text_threshold: options.textThreshold ?? DEFAULT_TEXT_THRESHOLD,
      ...(options.modelId ? { model_id: options.modelId } : {}),
    }),
    ...(signal ? { signal } : {}),
  });
}

/**
 * URL the canvas loads an image from.
 *
 * Goes through the backend rather than `file://`: the webview cannot read local
 * files directly, and routing through the API keeps the image-format allowlist in
 * front of every byte the UI renders.
 */
export function imageUrl(path: string): string {
  return `${API_BASE_URL}${API_PREFIX}/annotate/image?path=${encodeURIComponent(path)}`;
}

let counter = 0;

/** Give proposals the client-side ids the canvas keys on. */
export function toCanvasBoxes(response: ProposalResponse): CanvasBox[] {
  return response.boxes.map((box) => ({
    id: `proposed-${(counter += 1)}`,
    label: box.label,
    provenance: box.provenance,
    x: box.x,
    y: box.y,
    w: box.w,
    h: box.h,
    ...(box.score === undefined ? {} : { score: box.score }),
    ...(box.text === undefined ? {} : { text: box.text }),
  }));
}
