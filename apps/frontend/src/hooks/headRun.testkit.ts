/** Shared fixtures for the useHeadRun tests. Not a test file itself. */

import { vi } from 'vitest';


export const fetchMock = vi.fn<typeof fetch>();

export const HEAD = {
  id: 'h1',
  name: 'Depth probe',
  summary: 'Depth · trained on 1 dataset',
  kind: 'trained-here',
  head_type_id: 'linear-depth',
  task: 'depth',
  render_hint: 'depth-map',
  backbone_id: 'dinov2-small',
  backbone_family: 'dinov2',
  embed_dim: 384,
  num_classes: 0,
  class_names: [],
  dataset_ids: ['d1'],
  metrics: {},
  primary_metric: null,
  primary_metric_value: null,
  epochs_trained: 3,
  best_epoch: 2,
  source_repo: null,
  created_at: '2026-08-20T00:00:00Z',
};

export const FOUNDATION = {
  id: 'depth-anything-v2-small',
  title: 'Depth Anything V2 (small)',
  description: 'Monocular depth.',
  task: 'depth',
  render_hint: 'depth-map',
  model_id: 'depth-anything-v2-small',
  licence: 'Apache-2.0',
  non_commercial: false,
  installed: true,
  approx_size_mb: 95,
};

export function prediction(id: string, name: string) {
  return {
    instance_id: id,
    head_name: name,
    head_type_id: id,
    task: 'depth',
    render_hint: 'depth-map',
    class_names: [],
    payload: { depth_png: 'x', min: 0, max: 1, height: 4, width: 4 },
    grid: [0, 0],
    elapsed_ms: 10,
  };
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export interface Routes {
  foundations?: readonly unknown[];
  foundationStatus?: number;
}

export function route({ foundations = [FOUNDATION], foundationStatus = 200 }: Routes = {}): void {
  fetchMock.mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes('/foundation/predict')) {
      return Promise.resolve(
        foundationStatus === 200
          ? json(prediction('depth-anything-v2-small', 'Depth Anything V2 (small)'))
          : json({ error: { code: 'conflict', message: 'not installed' } }, foundationStatus),
      );
    }
    if (url.includes('/foundation')) return Promise.resolve(json({ foundations }));
    if (url.includes('/heads')) return Promise.resolve(json({ heads: [HEAD] }));
    if (url.includes('/inference/compose')) {
      return Promise.resolve(
        json({ predictions: [prediction('h1', 'Depth probe')], passes: 1, elapsed_ms: 50 }),
      );
    }
    return Promise.resolve(json({}));
  });
}


export const IMAGE = '/pics/a.jpg';

