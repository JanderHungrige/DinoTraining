/**
 * The estimate, and the frame URL (doc 68).
 *
 * The estimate is the number that changes the decision — someone who sees four minutes
 * picks a shorter range rather than cancelling three minutes in — so what matters is that
 * it is the right order of magnitude and that it moves in the right direction, not that it
 * is precise.
 */

import { describe, expect, it } from 'vitest';

import { describeEstimate, estimateSeconds, frameUrl } from './video';

describe('estimating a run', () => {
  it('scales with the number of frames', () => {
    const ten = estimateSeconds(10, ['rf-detr-nano'], 0);
    const hundred = estimateSeconds(100, ['rf-detr-nano'], 0);

    expect(hundred).toBeCloseTo(ten * 10);
  });

  it('knows Grounded SAM is the expensive one', () => {
    // ~5 s a frame against RF-DETR's ~0.15. Someone about to analyse 200 frames with it
    // should see "about 17 min" and choose differently.
    const grounded = estimateSeconds(100, ['grounded-sam'], 0);
    const detr = estimateSeconds(100, ['rf-detr-nano'], 0);

    expect(grounded).toBeGreaterThan(detr * 10);
  });

  it('charges every Grounded SAM tier the same', () => {
    // The bigger tiers are slower, not faster; treating `grounded-sam-large` as a cheap
    // unknown would under-quote the longest run in the app by a factor of thirty.
    for (const id of ['grounded-sam', 'grounded-sam-base', 'grounded-sam-large']) {
      expect(estimateSeconds(10, [id], 0)).toBeGreaterThan(10);
    }
  });

  it('does not charge N heads as N passes', () => {
    // Heads share one backbone pass (doc 18), so four heads is not four times one.
    const one = estimateSeconds(50, [], 1);
    const four = estimateSeconds(50, [], 4);

    expect(four).toBeLessThan(one * 2);
  });

  it('adds the models together', () => {
    const both = estimateSeconds(10, ['rf-detr-nano', 'grounded-sam'], 0);
    const each =
      estimateSeconds(10, ['rf-detr-nano'], 0) + estimateSeconds(10, ['grounded-sam'], 0);

    expect(both).toBeCloseTo(each);
  });

  it('is zero when nothing is selected', () => {
    expect(estimateSeconds(100, [], 0)).toBe(0);
  });
});

describe('saying the estimate out loud', () => {
  it('rounds a short run to seconds', () => {
    expect(describeEstimate(20)).toMatch(/20 sec/);
  });

  it('switches to minutes rather than saying 240 sec', () => {
    expect(describeEstimate(240)).toMatch(/4 min/);
  });

  it('switches to hours for the runs worth reconsidering', () => {
    // 18,000 frames of Grounded SAM. The number is the whole point of showing it.
    expect(describeEstimate(25_000)).toMatch(/hours/);
  });

  it('does not pretend to precision for a moment', () => {
    expect(describeEstimate(0.2)).toBe('a moment');
  });

  it('always reads as an estimate rather than a promise', () => {
    for (const seconds of [5, 200, 9000]) {
      expect(describeEstimate(seconds)).toMatch(/^about /);
    }
  });
});

describe('the frame URL', () => {
  it('carries the path and the index', () => {
    const url = frameUrl('/videos/clip.mp4', 42);

    expect(url).toContain('index=42');
    expect(url).toContain(encodeURIComponent('/videos/clip.mp4'));
  });

  it('encodes a path with spaces', () => {
    // "My Videos" is a real folder name and an unencoded space breaks the query.
    expect(frameUrl('/Users/j/My Videos/a.mp4', 0)).not.toMatch(/ /);
  });

  it('goes through the shared base, not a second builder', () => {
    // A second URL builder is how a frame request points at the wrong port in a packaged
    // build while every fetch keeps working.
    expect(frameUrl('/a.mp4', 0)).toContain('/api/v1/video/frame');
  });
});
