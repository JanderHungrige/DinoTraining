/**
 * A playback clock over N frames (doc 74): an index, playing or not, and a rate.
 *
 * The clock only moves the index; `FrameCanvas` decides what is on screen (drawn from its
 * cache, or the previous frame held), so a slow frame shows late rather than never.
 */

import { useCallback, useEffect, useState } from 'react';

export interface Playback {
  readonly index: number;
  readonly playing: boolean;
  readonly fps: number;
  readonly setIndex: (index: number) => void;
  readonly setFps: (fps: number) => void;
  readonly toggle: () => void;
  readonly step: (delta: number) => void;
}

export function usePlayback(length: number, initialFps: number, resetKey: string): Playback {
  const [index, setRawIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [fps, setFps] = useState(initialFps);

  // A new track starts at its beginning, paused, at its own rate.
  useEffect(() => {
    setRawIndex(0);
    setPlaying(false);
  }, [resetKey]);
  useEffect(() => setFps(initialFps), [initialFps]);

  const setIndex = useCallback(
    (next: number) => setRawIndex(Math.max(0, Math.min(length - 1, next))),
    [length],
  );

  useEffect(() => {
    if (!playing || length === 0) return;
    const timer = setInterval(() => {
      setRawIndex((current) => {
        if (current >= length - 1) {
          setPlaying(false);
          return current;
        }
        return current + 1;
      });
    }, 1000 / Math.max(0.5, fps));
    return () => clearInterval(timer);
  }, [playing, fps, length]);

  const toggle = useCallback(() => {
    setPlaying((current) => {
      // Play from the start again once the end has been reached, like any player.
      if (!current) setRawIndex((i) => (i >= length - 1 ? 0 : i));
      return !current;
    });
  }, [length]);

  const step = useCallback(
    (delta: number) => {
      setPlaying(false);
      setRawIndex((current) => Math.max(0, Math.min(length - 1, current + delta)));
    },
    [length],
  );

  return { index, playing, fps, setIndex, setFps, toggle, step };
}
