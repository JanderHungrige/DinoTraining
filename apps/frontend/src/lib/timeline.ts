/**
 * Where each class appears in a track, as the bars under the player (doc 75).
 *
 * Positions are indices into the track's frame list, not frame numbers: the bars span the
 * player's scrub range, so a frame and its place on the bar are the same number.
 */

export interface TimelineFrame {
  readonly classes: readonly string[];
}

/** A run of consecutive positions that all show the class, inclusive at both ends. */
export interface Segment {
  readonly start: number;
  readonly end: number;
}

/** Consecutive frames merge into one segment: a class seen for 300 frames is one bar, not
 *  300 elements, which is what keeps a long ride's timeline cheap to draw. */
export function segmentsFor(frames: readonly TimelineFrame[], name: string): Segment[] {
  const segments: Segment[] = [];
  let start = -1;
  frames.forEach((frame, position) => {
    const present = frame.classes.includes(name);
    if (present && start < 0) start = position;
    if (!present && start >= 0) {
      segments.push({ start, end: position - 1 });
      start = -1;
    }
  });
  if (start >= 0) segments.push({ start, end: frames.length - 1 });
  return segments;
}

/** The classes present in this track, in the dataset's class order (which is the colour). */
export function classesIn(
  frames: readonly TimelineFrame[],
  classNames: readonly string[],
): string[] {
  const present = new Set(frames.flatMap((frame) => frame.classes));
  return classNames.filter((name) => present.has(name));
}

export function countFrames(frames: readonly TimelineFrame[], name: string): number {
  return frames.filter((frame) => frame.classes.includes(name)).length;
}

export function firstOccurrence(frames: readonly TimelineFrame[], name: string): number | null {
  const found = frames.findIndex((frame) => frame.classes.includes(name));
  return found < 0 ? null : found;
}

/** The next position after `from` showing the class, or null. Never wraps: "next" past the
 *  last one staying put is clearer than a jump back to the start. */
export function nextOccurrence(
  frames: readonly TimelineFrame[],
  name: string,
  from: number,
): number | null {
  for (let position = from + 1; position < frames.length; position += 1) {
    if (frames[position]!.classes.includes(name)) return position;
  }
  return null;
}

export function previousOccurrence(
  frames: readonly TimelineFrame[],
  name: string,
  from: number,
): number | null {
  for (let position = Math.min(from, frames.length) - 1; position >= 0; position -= 1) {
    if (frames[position]!.classes.includes(name)) return position;
  }
  return null;
}
