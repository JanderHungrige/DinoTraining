import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { holdFor, runAutoplay, type AutoplayRun } from './autoplay';
import type { ImageReview } from './generatorSave';

const PATHS = ['/f/0.png', '/f/1.png', '/f/2.png', '/f/3.png'];

function review(path: string, boxes = 1): ImageReview {
  return {
    path,
    boxes: Array.from({ length: boxes }, (_, i) => ({ id: `${path}-${i}` }) as never),
    masks: [],
    maskResponse: null,
    imageSize: { width: 10, height: 10 },
  };
}

function run(overrides: Partial<AutoplayRun> = {}): AutoplayRun {
  return {
    paths: PATHS,
    start: 0,
    hidden: true,
    holdMs: 500,
    signal: new AbortController().signal,
    propose: vi.fn(async (path: string) => review(path)),
    save: vi.fn(async () => true),
    isSaved: () => false,
    show: vi.fn(),
    onProgress: vi.fn(),
    ...overrides,
  };
}

describe('runAutoplay (doc 71)', () => {
  it('starts from the chosen image and saves each one under its own path', async () => {
    const r = run({ start: 2 });
    const result = await runAutoplay(r);

    expect(vi.mocked(r.propose).mock.calls.map(([p]) => p)).toEqual(['/f/2.png', '/f/3.png']);
    expect(vi.mocked(r.save).mock.calls.map(([saved]) => saved.path)).toEqual([
      '/f/2.png',
      '/f/3.png',
    ]);
    expect(result).toMatchObject({ end: 'finished', total: 2, done: 2, saved: 2, lastIndex: 3 });
  });

  it('does not write an image where nothing was found', async () => {
    const r = run({ propose: vi.fn(async (path: string) => review(path, path === '/f/1.png' ? 0 : 1)) });
    const result = await runAutoplay(r);
    expect(r.save).toHaveBeenCalledTimes(3);
    expect(result).toMatchObject({ saved: 3, empty: 1, done: 4 });
  });

  it('skips images this session already saved, still counting them toward 100 %', async () => {
    const r = run({ isSaved: (path) => path === '/f/0.png' });
    const result = await runAutoplay(r);
    expect(r.propose).not.toHaveBeenCalledWith('/f/0.png');
    expect(result).toMatchObject({ skipped: 1, saved: 3, done: 4, total: 4 });
  });

  it('records a failed proposal and carries on', async () => {
    const r = run({
      propose: vi.fn(async (path: string) => {
        if (path === '/f/1.png') throw new Error('model not installed');
        return review(path);
      }),
    });
    const result = await runAutoplay(r);
    expect(result).toMatchObject({ end: 'finished', failed: 1, saved: 3 });
    expect(result.lastError).toBe('model not installed');
  });

  it('stops on a failed save instead of skipping past unsaved work', async () => {
    const r = run({ save: vi.fn(async (saved: ImageReview) => saved.path !== '/f/1.png') });
    const result = await runAutoplay(r);
    expect(result).toMatchObject({ end: 'save-failed', lastIndex: 1, saved: 1 });
    expect(r.propose).not.toHaveBeenCalledWith('/f/2.png');
  });

  it('reports progress after every image', async () => {
    const r = run();
    await runAutoplay(r);
    const dones = vi.mocked(r.onProgress).mock.calls.map(([p]) => p.done);
    expect(dones).toEqual([1, 2, 3, 4]);
  });

  it('in hidden mode draws nothing', async () => {
    const r = run({ hidden: true });
    await runAutoplay(r);
    expect(r.show).not.toHaveBeenCalled();
  });
});

describe('runAutoplay — visible mode and stopping', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('shows each image, then its proposal, then holds before saving', async () => {
    const r = run({ hidden: false, paths: ['/f/0.png'] });
    const done = runAutoplay(r);
    await vi.advanceTimersByTimeAsync(0);

    expect(vi.mocked(r.show).mock.calls.map(([i, rv]) => [i, rv?.path ?? null])).toEqual([
      [0, null],
      [0, '/f/0.png'],
    ]);
    // Still holding: the user gets half a second to see the box before it is written.
    expect(r.save).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(499);
    expect(r.save).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    await done;
    expect(r.save).toHaveBeenCalledTimes(1);
  });

  it('a stop during the hold leaves that image unsaved, on screen', async () => {
    const controller = new AbortController();
    const r = run({ hidden: false, signal: controller.signal });
    const done = runAutoplay(r);
    await vi.advanceTimersByTimeAsync(0);
    controller.abort();
    const result = await done;

    expect(result).toMatchObject({ end: 'stopped', lastIndex: 0, saved: 0 });
    expect(r.save).not.toHaveBeenCalled();
    expect(r.propose).toHaveBeenCalledTimes(1);
  });

  it('a stop while proposing shows the result but does not save it', async () => {
    const controller = new AbortController();
    let finish: (value: ImageReview) => void = () => undefined;
    const r = run({
      hidden: false,
      signal: controller.signal,
      propose: vi.fn(() => new Promise<ImageReview>((resolve) => (finish = resolve))),
    });
    const done = runAutoplay(r);
    await vi.advanceTimersByTimeAsync(0);
    controller.abort();
    finish(review('/f/0.png'));
    const result = await done;

    expect(result.end).toBe('stopped');
    expect(vi.mocked(r.show).mock.calls.at(-1)?.[1]?.path).toBe('/f/0.png');
    expect(r.save).not.toHaveBeenCalled();
  });
});

describe('holdFor', () => {
  it('resolves at once for an already-aborted signal', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(holdFor(10_000, controller.signal)).resolves.toBeUndefined();
  });
});
