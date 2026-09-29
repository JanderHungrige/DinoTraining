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

describe('runAutoplay — asking when unclear (doc 72)', () => {
  const BAND = { low: 0.3, high: 0.5 };

  function scored(path: string, scores: number[]): ImageReview {
    return {
      ...review(path, 0),
      boxes: scores.map((score, i) => ({ id: `${path}-${i}`, label: 'positive', score }) as never),
    };
  }

  it('pauses on an image with an in-band proposal, marked unclear, and saves the answer', async () => {
    const answered = scored('/f/0.png', [0.9]);
    const ask = vi.fn(
      async (_index: number, _review: ImageReview, _count: number): Promise<ImageReview> =>
        answered,
    );
    const r = run({
      paths: ['/f/0.png'],
      band: BAND,
      ask,
      propose: vi.fn(async (path: string) => scored(path, [0.9, 0.4])),
    });
    const result = await runAutoplay(r);

    const [index, asked, count] = ask.mock.calls[0]!;
    expect(index).toBe(0);
    expect(count).toBe(1);
    expect(asked.boxes.map((box: { label: string }) => box.label)).toEqual(['positive', 'unclear']);
    // What is saved is the user's answer, not the model's proposal.
    expect(vi.mocked(r.save).mock.calls[0]![0]).toBe(answered);
    expect(result).toMatchObject({ saved: 1, asked: 1 });
  });

  it('shows the image it asks about even in hidden mode', async () => {
    const r = run({
      paths: ['/f/0.png'],
      hidden: true,
      band: BAND,
      ask: vi.fn(async (_i: number, asked: ImageReview) => asked),
      propose: vi.fn(async (path: string) => scored(path, [0.4])),
    });
    await runAutoplay(r);
    expect(vi.mocked(r.show).mock.calls.map(([i, rv]) => [i, rv === null])).toEqual([
      [0, true],
      [0, false],
    ]);
  });

  it('does not ask when every score is outside the band', async () => {
    const ask = vi.fn();
    const r = run({
      paths: ['/f/0.png'],
      band: BAND,
      ask,
      propose: vi.fn(async (path: string) => scored(path, [0.9, 0.1])),
    });
    await runAutoplay(r);
    expect(ask).not.toHaveBeenCalled();
    expect(r.save).toHaveBeenCalledTimes(1);
  });

  it('stops there, unsaved, when the question is answered with Stop', async () => {
    const r = run({
      band: BAND,
      ask: vi.fn(async () => null),
      propose: vi.fn(async (path: string) => scored(path, [0.4])),
    });
    const result = await runAutoplay(r);
    expect(result).toMatchObject({ end: 'stopped', lastIndex: 0, saved: 0 });
    expect(r.save).not.toHaveBeenCalled();
  });

  it('never asks without a band, even with an ask handler', async () => {
    const ask = vi.fn();
    const r = run({ paths: ['/f/0.png'], band: null, ask });
    await runAutoplay(r);
    expect(ask).not.toHaveBeenCalled();
  });
});
