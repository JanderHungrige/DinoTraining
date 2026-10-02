/**
 * A single picture in "A video or a folder" (Jan, 2026-10-02): the viewer showed only
 * "That path is not a sequence", no picture, and "Run models" still ran (one backbone
 * pass) with nothing drawn, because results are drawn only in the single-image view.
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { InferenceViewerTab } from './InferenceViewerTab';

const fetchMock = vi.fn<typeof fetch>();
const PICTURE = '/Users/jan/Downloads/osdar23/rgb_center/000_1631177220.100000040.png';

const json = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

beforeEach(() => {
  localStorage.setItem('dinotraining.v1.viewer.mode', JSON.stringify('video'));
  localStorage.setItem('dinotraining.v1.viewer.path', JSON.stringify(PICTURE));
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset().mockImplementation((input: unknown) => {
    const url = String(input);
    if (url.includes('/heads')) {
      return Promise.resolve(json({ heads: [{ id: 'h1', name: 'Thermal spotter', summary: '', kind: 'trained-here', head_type_id: 'dense-detector', task: 'detection', render_hint: 'boxes', backbone_id: 'dinov2-small', backbone_family: 'dinov2', embed_dim: 384, num_classes: 1, class_names: ['person'], dataset_ids: [], metrics: {}, primary_metric: null, primary_metric_value: null, epochs_trained: 1, best_epoch: 1, source_repo: null, created_at: '2026-10-02T00:00:00+00:00' }] }));
    }
    if (url.includes('/inference/source')) {
      return Promise.resolve(json({ kind: 'file', root: PICTURE, truncated: false, items: [{ item_id: 'a', name: '000.png', path: PICTURE }] }));
    }
    if (url.includes('/video/probe')) return Promise.resolve(json({ detail: 'Not a video or a folder of frames.' }, 422));
    return Promise.resolve(json({}));
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('a single picture in the video mode', () => {
  it('cannot be run where nothing would be drawn, and opens as a single image', async () => {
    const user = userEvent.setup();
    render(<InferenceViewerTab />);
    await user.click(await screen.findByRole('checkbox', { name: /Thermal spotter/ }));
    expect(await screen.findByText(/That path is not a sequence/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^Run/ })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Open it as a single image' }));
    await waitFor(() => expect(screen.getByRole('radio', { name: /A single image/ })).toBeChecked());
    expect((await screen.findAllByRole('img', { name: '000.png' })).length).toBeGreaterThan(0); // original and result pane
    expect(screen.getByRole('button', { name: /^Run/ })).toBeEnabled();
  });
});
