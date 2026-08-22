/**
 * Foundation-model slice of the API contract. Mirrors backend/app/api/v1/foundation.py.
 *
 * A foundation model predicts on its own — no backbone, no head, no shared pass. It still
 * returns a `Prediction`, which is what lets the viewer put it in a pane beside a trained
 * head and the overlay registry draw it without knowing the difference.
 */

import { apiFetch } from './client';
import { isPrediction, type Prediction } from './inference';

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
    }),
    ...(signal ? { signal } : {}),
  });
}
