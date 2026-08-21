/** Shared fixtures for the SessionSetup tests. Not a test file itself. */

import { render, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { SessionSetup } from './SessionSetup';

export const fetchMock = vi.fn<typeof fetch>();



export function head(overrides: Partial<HeadInstanceInfo> = {}): HeadInstanceInfo {
  return {
    id: 'h1',
    name: 'Thermal spotter',
    summary: 'Object detection · 2 classes · trained on 1 dataset',
    kind: 'trained-here',
    head_type_id: 'dense-detector',
    task: 'detection',
    render_hint: 'boxes',
    backbone_id: 'dinov2-small',
    backbone_family: 'dinov2',
    embed_dim: 384,
    num_classes: 2,
    class_names: ['dog', 'person'],
    dataset_ids: ['d1'],
    metrics: {},
    primary_metric: null,
    primary_metric_value: null,
    epochs_trained: 5,
    best_epoch: 4,
    source_repo: null,
    created_at: '2026-08-20T00:00:00+00:00',
    ...overrides,
  };
}

export function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

export const CREATED = {
  id: 'ds-new',
  name: 'Thermal',
  created_at: '2026-08-20T00:00:00+00:00',
  prompt: null,
  copy_images: false,
  counts: { images: 0, boxes: 0, masks: 0, positive: 0, negative: 0, unclear: 0 },
};

export const DETECTOR = {
  id: 'rf-detr-nano',
  title: 'RF-DETR (nano)',
  description: 'General object detection, 91 COCO classes.',
  task: 'detection',
  render_hint: 'boxes',
  model_id: 'rf-detr-nano',
  licence: 'Apache-2.0',
  non_commercial: false,
  installed: true,
  approx_size_mb: 116,
  takes_concept: false,
};

export const DEPTH = { ...DETECTOR, id: 'depth-anything-v2-small', title: 'Depth Anything V2', render_hint: 'depth-map', task: 'depth' };

export function routes(
  heads: readonly HeadInstanceInfo[],
  foundations: readonly unknown[] = [DETECTOR, DEPTH],
): void {
  fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/foundation')) return Promise.resolve(json({ foundations }));
    if (url.includes('/heads')) return Promise.resolve(json({ heads }));
    // Route by method, not just path: submitting creates the dataset before it starts,
    // and a list-shaped body there fails validation and swallows the whole submit.
    if (url.includes('/datasets') && init?.method === 'POST') {
      return Promise.resolve(json(CREATED));
    }
    if (url.includes('/datasets')) return Promise.resolve(json({ datasets: [] }));
    return Promise.resolve(json({}));
  });
}

export async function setup(
  heads: readonly HeadInstanceInfo[] = [head()],
  foundations: readonly unknown[] = [DETECTOR, DEPTH],
) {
  routes(heads, foundations);
  const onStart = vi.fn();
  render(<SessionSetup onStart={onStart} />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  return { onStart, user: userEvent.setup() };
}

