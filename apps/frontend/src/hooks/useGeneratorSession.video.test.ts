/**
 * Doc 73: a video source is decoded into the destination dataset, and every save records
 * where the image sits in its sequence — the video's frame number, or a folder's position.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExpertProposalResponse } from '../api/generate';
import type { GeneratorConfig } from '../types/generatorConfig';
import { useGeneratorSession } from './useGeneratorSession';

vi.mock('../api/annotate', () => ({ listFolderImages: vi.fn() }));
vi.mock('../api/videoExtract', () => ({ extractFrames: vi.fn() }));
vi.mock('../api/datasets', async (original) => ({
  ...(await original<Record<string, unknown>>()),
  saveImageBoxes: vi.fn(),
}));
vi.mock('../api/generate', async () => {
  const actual = await vi.importActual<typeof import('../api/generate')>('../api/generate');
  return { ...actual, proposeWithExpertHead: vi.fn() };
});

const annotate = await import('../api/annotate');
const extract = await import('../api/videoExtract');
const datasets = await import('../api/datasets');
const generate = await import('../api/generate');

const BASE = {
  kind: 'expert' as const,
  datasetId: 'd1',
  backboneId: 'dinov2-small',
  instanceId: 'h1',
  scoreThreshold: 0.3,
};

const PROPOSAL: ExpertProposalResponse = {
  image_path: '/x',
  width: 64,
  height: 48,
  device: 'cpu',
  head_name: 'Rail',
  head_summary: 'Detection',
  boxes: [
    {
      label: 'positive',
      provenance: 'expert-head',
      x: 1,
      y: 2,
      w: 3,
      h: 4,
      prompt: 'signal',
      score: 0.9,
      producer: { id: 'h1', label: 'Rail' },
    },
  ],
};

beforeEach(() => {
  vi.mocked(generate.proposeWithExpertHead).mockResolvedValue(PROPOSAL);
  vi.mocked(datasets.saveImageBoxes).mockResolvedValue({
    images: 1, boxes: 1, masks: 0, positive: 1, negative: 0, unclear: 0,
  } as never);
});
afterEach(() => vi.clearAllMocks());

async function proposeAndSave(config: GeneratorConfig, advance = 0) {
  const { result } = renderHook(() => useGeneratorSession(config));
  await waitFor(() => expect(result.current.currentImage).not.toBeNull());
  for (let i = 0; i < advance; i += 1) {
    await act(async () => {
      await result.current.next();
    });
  }
  await act(async () => {
    const review = await result.current.propose();
    await result.current.save(review!);
  });
  return vi.mocked(datasets.saveImageBoxes).mock.calls[0]!;
}

describe('useGeneratorSession — sequences (doc 73)', () => {
  it('decodes a video into the destination dataset and saves each frame with its number', async () => {
    vi.mocked(extract.extractFrames).mockResolvedValue([
      { index: 30, path: '/data/d1/frames/track/track-f000030.jpg' },
      { index: 40, path: '/data/d1/frames/track/track-f000040.jpg' },
    ]);
    const config: GeneratorConfig = {
      ...BASE,
      images: { kind: 'video', path: '/v/track.mp4', range: { start: 30, count: 2, stride: 10 } },
    };
    const [, image, , frame] = await proposeAndSave(config, 1);

    const [request] = vi.mocked(extract.extractFrames).mock.calls[0]!;
    expect(request).toEqual({
      source: '/v/track.mp4',
      datasetId: 'd1',
      start: 30,
      count: 2,
      stride: 10,
    });
    expect(image.path).toBe('/data/d1/frames/track/track-f000040.jpg');
    // The video's own frame number, not the position in the decoded list.
    expect(frame).toEqual({ sequence: '/v/track.mp4', frame_index: 40 });
  });

  it('records a folder image by its place in the folder', async () => {
    vi.mocked(annotate.listFolderImages).mockResolvedValue(['/f/a.png', '/f/b.png', '/f/c.png']);
    const config: GeneratorConfig = { ...BASE, images: { kind: 'folder', folder: '/f' } };
    const [, image, , frame] = await proposeAndSave(config, 2);
    expect(image.path).toBe('/f/c.png');
    expect(frame).toEqual({ sequence: '/f', frame_index: 2 });
  });

  it('reports decoding progress while the video is being decoded', async () => {
    let report: (p: { done: number; total: number }) => void = () => undefined;
    vi.mocked(extract.extractFrames).mockImplementation((_request, onProgress) => {
      report = onProgress;
      return new Promise(() => undefined);
    });
    const config: GeneratorConfig = {
      ...BASE,
      images: { kind: 'video', path: '/v/track.mp4', range: { start: 0, count: 50, stride: 1 } },
    };
    const { result } = renderHook(() => useGeneratorSession(config));
    await waitFor(() => expect(extract.extractFrames).toHaveBeenCalled());
    act(() => report({ done: 12, total: 50 }));
    expect(result.current.loading).toBe(true);
    expect(result.current.decoding).toEqual({ done: 12, total: 50 });
  });

  it('shows why a video could not be decoded', async () => {
    vi.mocked(extract.extractFrames).mockRejectedValue(new Error('Could not decode track.mp4'));
    const config: GeneratorConfig = {
      ...BASE,
      images: { kind: 'video', path: '/v/track.mp4', range: { start: 0, count: 5, stride: 1 } },
    };
    const { result } = renderHook(() => useGeneratorSession(config));
    await waitFor(() => expect(result.current.error).toBe('Could not decode track.mp4'));
    expect(result.current.decoding).toBeNull();
  });
});
