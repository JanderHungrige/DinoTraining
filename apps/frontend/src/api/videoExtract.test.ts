import { afterEach, describe, expect, it, vi } from 'vitest';

import { extractFrames, type ExtractJob } from './videoExtract';

vi.mock('./client', () => ({ apiFetch: vi.fn() }));
const client = await import('./client');

function job(overrides: Partial<ExtractJob>): ExtractJob {
  return { job_id: 'j1', state: 'running', done: 0, total: 3, message: '', frames: [], ...overrides };
}

const REQUEST = { source: '/v/track.mp4', datasetId: 'd1', start: 0, count: 3, stride: 1 };
const FRAMES = [
  { index: 0, path: '/data/f0.jpg' },
  { index: 1, path: '/data/f1.jpg' },
];

afterEach(() => vi.clearAllMocks());

describe('extractFrames (doc 73)', () => {
  it('starts, polls until complete, and reports progress on the way', async () => {
    vi.mocked(client.apiFetch)
      .mockResolvedValueOnce(job({}))
      .mockResolvedValueOnce(job({ done: 1 }))
      .mockResolvedValueOnce(job({ state: 'complete', done: 2, total: 2, frames: FRAMES }));
    const progress: number[] = [];

    const frames = await extractFrames(
      REQUEST,
      (p) => progress.push(p.done),
      new AbortController().signal,
      1,
    );

    expect(frames).toEqual(FRAMES);
    expect(progress).toEqual([0, 1, 2]);
    const [url, , init] = vi.mocked(client.apiFetch).mock.calls[0]!;
    expect(url).toBe('/video/extract');
    expect(JSON.parse(String((init as RequestInit).body))).toMatchObject({
      source: '/v/track.mp4',
      dataset_id: 'd1',
      count: 3,
    });
  });

  it("rejects with the job's own reason when decoding fails", async () => {
    vi.mocked(client.apiFetch)
      .mockResolvedValueOnce(job({}))
      .mockResolvedValueOnce(job({ state: 'failed', message: 'Could not decode track.mp4' }));
    await expect(
      extractFrames(REQUEST, () => undefined, new AbortController().signal, 1),
    ).rejects.toThrow('Could not decode track.mp4');
  });

  it('cancels the job on the server when the caller gives up', async () => {
    const controller = new AbortController();
    vi.mocked(client.apiFetch).mockImplementation(async (_url: string, _guard, init) => {
      if ((init as RequestInit | undefined)?.method === 'DELETE') return job({ state: 'cancelled' });
      return job({});
    });
    const running = extractFrames(REQUEST, () => controller.abort(), controller.signal, 1);
    await expect(running).rejects.toThrow();
    const deletes = vi
      .mocked(client.apiFetch)
      .mock.calls.filter(([, , init]) => (init as RequestInit | undefined)?.method === 'DELETE');
    expect(deletes).toHaveLength(1);
    expect(deletes[0]![0]).toBe('/video/extract/j1');
  });
});
