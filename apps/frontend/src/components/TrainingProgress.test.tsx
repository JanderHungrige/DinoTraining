/**
 * Tests for the live-progress rendering rules.
 *
 * The metric-key test is the important one: charts must follow whatever the head type
 * declared, so a segmenter reporting mIoU works with no frontend change.
 */

import { describe, expect, it } from 'vitest';

import { metricKeys, type EpochInfo } from '../api/training';
import { sparklinePath } from './TrainingProgress';

function epoch(n: number, metrics: Record<string, number>): EpochInfo {
  return { epoch: n, train_loss: 1 / n, val_loss: 1 / n, metrics };
}

describe('metricKeys', () => {
  it('reads keys from the payload rather than a fixed list', () => {
    const history = [epoch(1, { miou: 0.3, pixel_accuracy: 0.8 })];
    expect(metricKeys(history)).toEqual(['miou', 'pixel_accuracy']);
  });

  it('preserves first-seen order across epochs', () => {
    const history = [epoch(1, { map: 0.1, map_50: 0.2 }), epoch(2, { map: 0.3, map_75: 0.4 })];
    expect(metricKeys(history)).toEqual(['map', 'map_50', 'map_75']);
  });

  it('does not duplicate a key seen every epoch', () => {
    expect(metricKeys([epoch(1, { accuracy: 0.5 }), epoch(2, { accuracy: 0.7 })])).toEqual([
      'accuracy',
    ]);
  });

  it('returns nothing for an empty history', () => {
    expect(metricKeys([])).toEqual([]);
  });
});

describe('sparklinePath', () => {
  it('is empty with no data', () => {
    expect(sparklinePath([])).toBe('');
  });

  it('draws a flat mid-height line for a single point', () => {
    expect(sparklinePath([0.5], 120, 24)).toBe('M0,12 L120,12');
  });

  it('puts a flat series mid-height rather than at zero', () => {
    // A constant series collapsing to the baseline reads as "no data".
    const path = sparklinePath([0.9, 0.9, 0.9], 120, 24);
    expect(path).toContain('12.0');
    expect(path).not.toContain('24.0');
  });

  it('spans the full height for a rising series', () => {
    const path = sparklinePath([0, 1], 120, 24);
    expect(path).toBe('M0.0,24.0 L120.0,0.0');
  });

  it('emits one segment per point', () => {
    const path = sparklinePath([0, 0.5, 1]);
    expect(path.split('L')).toHaveLength(3);
  });
});
