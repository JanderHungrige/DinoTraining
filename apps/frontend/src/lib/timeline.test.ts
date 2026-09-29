import { describe, expect, it } from 'vitest';

import {
  classesIn,
  countFrames,
  firstOccurrence,
  nextOccurrence,
  previousOccurrence,
  segmentsFor,
} from './timeline';

// signal on 1–3 and 6; train on 4 and the last frame.
const FRAMES = [
  [],
  ['signal'],
  ['signal'],
  ['signal', 'train'],
  ['train'],
  [],
  ['signal'],
  ['train'],
].map((classes) => ({ classes }));

describe('timeline (doc 75)', () => {
  it('merges consecutive frames into one segment', () => {
    expect(segmentsFor(FRAMES, 'signal')).toEqual([
      { start: 1, end: 3 },
      { start: 6, end: 6 },
    ]);
  });

  it('closes a segment that runs to the last frame', () => {
    expect(segmentsFor(FRAMES, 'train')).toEqual([
      { start: 3, end: 4 },
      { start: 7, end: 7 },
    ]);
  });

  it('has no segments for a class that never appears', () => {
    expect(segmentsFor(FRAMES, 'person')).toEqual([]);
  });

  it('lists the classes present, in the dataset order that decides their colour', () => {
    expect(classesIn(FRAMES, ['person', 'signal', 'train'])).toEqual(['signal', 'train']);
  });

  it('counts the frames a class is on', () => {
    expect(countFrames(FRAMES, 'signal')).toBe(4);
  });

  it('finds the first, next and previous occurrence', () => {
    expect(firstOccurrence(FRAMES, 'train')).toBe(3);
    expect(nextOccurrence(FRAMES, 'signal', 3)).toBe(6);
    expect(previousOccurrence(FRAMES, 'signal', 6)).toBe(3);
    expect(firstOccurrence(FRAMES, 'person')).toBeNull();
  });

  it('never wraps past either end', () => {
    expect(nextOccurrence(FRAMES, 'train', 7)).toBeNull();
    expect(previousOccurrence(FRAMES, 'signal', 1)).toBeNull();
  });
});
