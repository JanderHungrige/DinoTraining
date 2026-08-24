import { describe, expect, it } from 'vitest';

import {
  IDENTITY,
  MAX_SCALE,
  MIN_SCALE,
  clampTransform,
  panBy,
  zoomAt,
  type ViewTransform,
} from './viewTransform';

const SIZE = { width: 400, height: 300 };

function at(scale: number, tx = 0, ty = 0): ViewTransform {
  return { scale, tx, ty };
}

describe('clampTransform', () => {
  it('pins translation to zero at fit scale', () => {
    // Panning an image that already fits would move it off its own frame for no gain.
    expect(clampTransform(at(1, 120, -80), SIZE)).toEqual(IDENTITY);
  });

  it('keeps the scaled content covering the container', () => {
    // At 2x the content is 800 wide in a 400 container, so tx may run from -400 to 0.
    expect(clampTransform(at(2, 50, 0), SIZE).tx).toBe(0);
    expect(clampTransform(at(2, -900, 0), SIZE).tx).toBe(-400);
    expect(clampTransform(at(2, -250, 0), SIZE).tx).toBe(-250);
  });

  it('clamps each axis against its own dimension', () => {
    expect(clampTransform(at(2, -999, -999), SIZE)).toEqual({ scale: 2, tx: -400, ty: -300 });
  });

  it('holds the scale inside its bounds', () => {
    expect(clampTransform(at(0.2), SIZE).scale).toBe(MIN_SCALE);
    expect(clampTransform(at(99), SIZE).scale).toBe(MAX_SCALE);
  });
});

describe('zoomAt', () => {
  it('keeps the point under the cursor under the cursor', () => {
    // The whole reason zoom is not about the centre: the user points at a detail and
    // it must not slide away.
    const focusX = 300;
    const focusY = 200;
    const before = at(2, -100, -50);

    const after = zoomAt(before, focusX, focusY, 2, SIZE);

    // Image-space coordinate under the focus point, before and after.
    const imageXBefore = (focusX - before.tx) / before.scale;
    const imageXAfter = (focusX - after.tx) / after.scale;
    expect(imageXAfter).toBeCloseTo(imageXBefore, 6);

    const imageYBefore = (focusY - before.ty) / before.scale;
    const imageYAfter = (focusY - after.ty) / after.scale;
    expect(imageYAfter).toBeCloseTo(imageYBefore, 6);
  });

  it('multiplies the scale by the factor', () => {
    expect(zoomAt(at(2, -100, -100), 200, 150, 1.5, SIZE).scale).toBeCloseTo(3);
  });

  it('cannot zoom out past fit', () => {
    const result = zoomAt(at(1.2, -20, -10), 200, 150, 0.1, SIZE);

    expect(result.scale).toBe(MIN_SCALE);
    // And the clamp then forces the translation back, so no blank gutter is left behind.
    expect(result).toEqual(IDENTITY);
  });

  it('cannot zoom in past the maximum', () => {
    expect(zoomAt(at(MAX_SCALE, 0, 0), 200, 150, 4, SIZE).scale).toBe(MAX_SCALE);
  });

  it('never leaves the content off the container', () => {
    // Zoom out hard at a corner — the naive maths puts the content's edge inside the frame.
    const result = zoomAt(at(8, -2000, -1500), 0, 0, 0.5, SIZE);

    expect(result.tx).toBeLessThanOrEqual(0);
    expect(result.tx).toBeGreaterThanOrEqual(SIZE.width * (1 - result.scale));
  });
});

describe('panBy', () => {
  it('translates and clamps in one step', () => {
    expect(panBy(at(2, -100, -100), 40, 25, SIZE)).toEqual({ scale: 2, tx: -60, ty: -75 });
  });

  it('does nothing at fit scale', () => {
    expect(panBy(IDENTITY, 50, 50, SIZE)).toEqual(IDENTITY);
  });

  it('stops at the edge rather than running past it', () => {
    expect(panBy(at(2, -20, 0), 999, 0, SIZE).tx).toBe(0);
  });
});
