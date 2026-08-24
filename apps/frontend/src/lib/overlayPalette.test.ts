import { describe, expect, it } from 'vitest';

import { classColour, depthColour, toCssColour } from './overlayPalette';

describe('classColour', () => {
  it('is stable for an index', () => {
    // Two runs of the same head must be comparable; a colour that moved between runs
    // would read as a different prediction.
    expect(classColour(37)).toEqual(classColour(37));
  });

  it('gives adjacent indices visibly different colours', () => {
    // Adjacent class ids are what adjacent regions of a segmentation usually are, so
    // near-identical colours for them would hide the boundary.
    const distance = (a: number, b: number): number => {
      const x = classColour(a);
      const y = classColour(b);
      return Math.abs(x.r - y.r) + Math.abs(x.g - y.g) + Math.abs(x.b - y.b);
    };

    for (let i = 0; i < 20; i += 1) {
      expect(distance(i, i + 1)).toBeGreaterThan(60);
    }
  });

  it('keeps 150 classes distinct enough to tell apart', () => {
    // ADE20k is 150 classes and is a default head, so this is a real case, not a limit.
    const seen = new Set<string>();
    for (let i = 0; i < 150; i += 1) seen.add(toCssColour(classColour(i)));

    expect(seen.size).toBe(150);
  });

  it('stays inside the byte range', () => {
    for (const index of [0, 1, 149, 255, 1000]) {
      const { r, g, b } = classColour(index);
      for (const channel of [r, g, b]) {
        expect(channel).toBeGreaterThanOrEqual(0);
        expect(channel).toBeLessThanOrEqual(255);
      }
    }
  });
});

describe('depthColour', () => {
  it('gets monotonically lighter with distance', () => {
    // The ramp must not cycle: a hue that comes back around makes the eye read a
    // boundary where the data has none.
    const luminance = (t: number): number => {
      const { r, g, b } = depthColour(t);
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };

    for (let t = 0; t < 1; t += 0.05) {
      expect(luminance(t + 0.05)).toBeGreaterThan(luminance(t));
    }
  });

  it('clamps out-of-range input rather than producing nonsense', () => {
    expect(depthColour(-5)).toEqual(depthColour(0));
    expect(depthColour(9)).toEqual(depthColour(1));
  });
});

describe('toCssColour', () => {
  it('omits the alpha channel when fully opaque', () => {
    expect(toCssColour({ r: 1, g: 2, b: 3 })).toBe('rgb(1 2 3)');
  });

  it('includes alpha when translucent', () => {
    expect(toCssColour({ r: 1, g: 2, b: 3 }, 0.5)).toBe('rgb(1 2 3 / 0.5)');
  });
});
