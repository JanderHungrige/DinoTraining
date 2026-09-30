/**
 * Editing an outline (doc 106). Mirrors backend/app/api/v1/segment.py.
 */

import { apiFetch } from './client';
import { arrayOf, hasFields, isRecord, jsonBody } from './prepGuards';
import type { CanvasMask } from '../types/annotation';

export interface EditedMask {
  readonly rle: CanvasMask['rle'];
  readonly mask_png: string;
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly score: number | null;
}

export interface Rect {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
}

export interface ClickPoint {
  readonly x: number;
  readonly y: number;
  readonly positive: boolean;
}

const isEdited = (v: unknown): v is EditedMask =>
  hasFields(v, { rle: 'object', mask_png: 'string', x: 'number', y: 'number', w: 'number', h: 'number' });

export function refineOutline(imagePath: string, box: Rect, points: readonly ClickPoint[]): Promise<EditedMask> {
  return apiFetch('/segment/refine', isEdited, jsonBody({ image_path: imagePath, box, points }));
}

export async function outlinesFromBoxes(imagePath: string, boxes: readonly Rect[]): Promise<EditedMask[]> {
  const body = await apiFetch(
    '/segment/boxes',
    (v: unknown): v is { masks: EditedMask[] } => isRecord(v) && arrayOf(isEdited)(v['masks']),
    jsonBody({ image_path: imagePath, boxes }),
  );
  return body.masks;
}

export function strokeOutline(
  rle: CanvasMask['rle'],
  points: readonly (readonly [number, number])[],
  radius: number,
  erase: boolean,
): Promise<EditedMask> {
  return apiFetch('/segment/stroke', isEdited, jsonBody({ rle, points, radius, erase }));
}
