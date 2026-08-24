/**
 * Choosing heads before there is an image (doc 34).
 *
 * Wave 3 rendered the head panel inside a `{current && …}` guard, so the slowest decision
 * in the tab — which of N heads to compare — sat behind a folder read. The state was never
 * the problem: `useHeadRun` already lived at tab level and survived image changes. Only
 * the panel was gated, which is why these tests assert on what is *rendered* with no image
 * loaded, and on the Run button staying disabled until there is one.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { InferenceViewerTab } from './InferenceViewerTab';

const fetchMock = vi.fn<typeof fetch>();

function head(overrides: Partial<HeadInstanceInfo> = {}): HeadInstanceInfo {
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

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes('/heads')) return Promise.resolve(json({ heads: [head()] }));
    return Promise.resolve(json({}));
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe('before any image is loaded', () => {
  it('still offers the heads', async () => {
    render(<InferenceViewerTab />);
    expect(await screen.findByRole('checkbox', { name: /Thermal spotter/ })).toBeInTheDocument();
  });

  it('says what is missing rather than showing an inert panel', async () => {
    render(<InferenceViewerTab />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(screen.getByRole('status')).toHaveTextContent(/Pick an image or a folder/);
  });

  it('lets a head be selected with nothing loaded', async () => {
    const user = userEvent.setup();
    render(<InferenceViewerTab />);

    const box = await screen.findByRole('checkbox', { name: /Thermal spotter/ });
    await user.click(box);

    expect(box).toBeChecked();
  });

  it('keeps Run disabled — a selection is not something to run yet', async () => {
    const user = userEvent.setup();
    render(<InferenceViewerTab />);

    await user.click(await screen.findByRole('checkbox', { name: /Thermal spotter/ }));

    // The whole point of lifting the panel: selecting is allowed, running is not.
    expect(screen.getByRole('button', { name: /^Run/ })).toBeDisabled();
  });

  it('never calls the inference endpoint without an image', async () => {
    const user = userEvent.setup();
    render(<InferenceViewerTab />);

    await user.click(await screen.findByRole('checkbox', { name: /Thermal spotter/ }));

    expect(
      fetchMock.mock.calls.some(([input]) => String(input).includes('/inference')),
    ).toBe(false);
  });
});
