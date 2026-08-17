import { describe, expect, it } from 'vitest';

import {
  clamp,
  fitContain,
  isDeliberateDrag,
  rectFromPoints,
  toDisplay,
  toNatural,
  type RenderedImage,
} from './geometry';

/** A 200x100 image rendered at half scale inside a 200x200 container. */
const HALF: RenderedImage = {
  width: 100,
  height: 50,
  offsetX: 50,
  offsetY: 75,
  naturalWidth: 200,
  naturalHeight: 100,
};

describe('clamp', () => {
  it('passes a value inside the range through', () => {
    expect(clamp(5, 0, 10)).toBe(5);
  });

  it('clamps below and above', () => {
    expect(clamp(-3, 0, 10)).toBe(0);
    expect(clamp(30, 0, 10)).toBe(10);
  });
});

describe('fitContain', () => {
  it('letterboxes vertically when the image is wider than the container', () => {
    const rendered = fitContain(200, 200, 200, 100);
    expect(rendered.width).toBe(200);
    expect(rendered.height).toBe(100);
    expect(rendered.offsetY).toBe(50);
    expect(rendered.offsetX).toBe(0);
  });

  it('letterboxes horizontally when the image is taller', () => {
    const rendered = fitContain(200, 200, 100, 200);
    expect(rendered.width).toBe(100);
    expect(rendered.offsetX).toBe(50);
    expect(rendered.offsetY).toBe(0);
  });

  it('fills exactly when the aspect ratios match', () => {
    const rendered = fitContain(400, 200, 200, 100);
    expect([rendered.offsetX, rendered.offsetY]).toEqual([0, 0]);
    expect(rendered.width).toBe(400);
  });

  it('never scales beyond the smaller axis', () => {
    const rendered = fitContain(1000, 100, 200, 100);
    expect(rendered.height).toBeLessThanOrEqual(100);
  });

  it('returns a zero box for degenerate inputs', () => {
    expect(fitContain(0, 0, 200, 100).width).toBe(0);
    expect(fitContain(200, 200, 0, 0).width).toBe(0);
  });
});

describe('toDisplay', () => {
  it('scales and offsets a box', () => {
    expect(toDisplay({ x: 20, y: 10, w: 40, h: 20 }, HALF)).toEqual({
      x: 60,
      y: 80,
      w: 20,
      h: 10,
    });
  });

  it('maps the origin to the image offset', () => {
    expect(toDisplay({ x: 0, y: 0, w: 0, h: 0 }, HALF)).toMatchObject({ x: 50, y: 75 });
  });
});

describe('toNatural', () => {
  it('is the inverse of toDisplay', () => {
    const original = { x: 20, y: 10, w: 40, h: 20 };
    expect(toNatural(toDisplay(original, HALF), HALF)).toEqual(original);
  });

  it('clamps a drag that runs off the right edge', () => {
    const natural = toNatural({ x: 100, y: 80, w: 500, h: 10 }, HALF);
    expect(natural.x + natural.w).toBeLessThanOrEqual(HALF.naturalWidth);
  });

  it('clamps a drag that starts above the image', () => {
    const natural = toNatural({ x: 60, y: 0, w: 20, h: 20 }, HALF);
    expect(natural.y).toBe(0);
  });

  it('clamps a drag entirely outside to zero area', () => {
    const natural = toNatural({ x: 0, y: 0, w: 10, h: 10 }, HALF);
    expect(natural.w * natural.h).toBe(0);
  });

  it('returns a zero rect when nothing is rendered', () => {
    const empty: RenderedImage = { ...HALF, width: 0, height: 0 };
    expect(toNatural({ x: 1, y: 2, w: 3, h: 4 }, empty)).toEqual({ x: 0, y: 0, w: 0, h: 0 });
  });
});

describe('rectFromPoints', () => {
  it('handles a top-left to bottom-right drag', () => {
    expect(rectFromPoints(10, 10, 40, 30)).toEqual({ x: 10, y: 10, w: 30, h: 20 });
  });

  it('normalises a drag made upward and leftward', () => {
    expect(rectFromPoints(40, 30, 10, 10)).toEqual({ x: 10, y: 10, w: 30, h: 20 });
  });

  it('yields zero area for a click', () => {
    expect(rectFromPoints(5, 5, 5, 5)).toEqual({ x: 5, y: 5, w: 0, h: 0 });
  });
});

describe('isDeliberateDrag', () => {
  it('rejects a stray click', () => {
    expect(isDeliberateDrag({ x: 0, y: 0, w: 1, h: 1 })).toBe(false);
  });

  it('rejects a drag that is thin in one axis', () => {
    expect(isDeliberateDrag({ x: 0, y: 0, w: 100, h: 2 })).toBe(false);
  });

  it('accepts a real drag', () => {
    expect(isDeliberateDrag({ x: 0, y: 0, w: 20, h: 20 })).toBe(true);
  });
});
