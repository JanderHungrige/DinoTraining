/**
 * The prepass and the playback clock (doc 68).
 *
 * Two things that look like one and are deliberately kept apart: a **run** is a job on the
 * backend with progress and a cancel, and **playback** is a timer walking an index. The
 * player can be paused while the run is still going, and scrubbed anywhere in the part
 * that has finished — which is only possible because neither drives the other.
 *
 * Predictions accumulate into a map keyed by frame index. Polling asks only for the window
 * that has completed since the last poll, so a 500-frame run does not re-send everything
 * it has every second.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import {
  cancelRun,
  pollRun,
  startRun,
  type FramePredictions,
  type SequenceRun,
  type StartRunRequest,
} from '../api/video';
import type { Prediction } from '../api/inference';

/** How often to ask the backend how far it has got. */
const POLL_MS = 700;

export interface SequenceRunState {
  readonly run: SequenceRun | null;
  readonly error: string | null;
  /** Frame index → what the models said about it. Sparse while the run is going. */
  readonly byFrame: ReadonlyMap<number, readonly Prediction[]>;
  readonly index: number;
  readonly playing: boolean;
  readonly start: (request: StartRunRequest) => Promise<void>;
  readonly stop: () => Promise<void>;
  readonly setIndex: (index: number) => void;
  readonly setPlaying: (playing: boolean) => void;
  readonly clear: () => void;
}

function describe(cause: unknown): string {
  return cause instanceof ApiError ? cause.message : 'The run could not be started.';
}

export function useSequenceRun(fps: number): SequenceRunState {
  const [run, setRun] = useState<SequenceRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [byFrame, setByFrame] = useState<ReadonlyMap<number, readonly Prediction[]>>(
    new Map(),
  );
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  // How far the *frames* have been collected. **Absolute**, in the source's own numbering,
  // because that is what the backend's `since`/`until` mean — a run over frames 200..320
  // polled from 0 asks for a window it never produced and collects nothing at all.
  //
  // Not the same as `run.done` either: a poll can report progress whose frames it did not
  // carry, and asking again from the wrong mark would silently skip them.
  const collected = useRef(0);

  const clear = useCallback((): void => {
    setRun(null);
    setError(null);
    setByFrame(new Map());
    setIndex(0);
    setPlaying(false);
    collected.current = 0;
  }, []);

  const start = useCallback(
    async (request: StartRunRequest): Promise<void> => {
      clear();
      try {
        const started = await startRun(request);
        collected.current = started.start;
        setRun(started);
      } catch (cause: unknown) {
        setError(describe(cause));
      }
    },
    [clear],
  );

  const stop = useCallback(async (): Promise<void> => {
    if (!run || run.state === 'complete') return;
    try {
      // The response carries the run's final shape; a cancelled run keeps its frames.
      setRun(await cancelRun(run.job_id));
    } catch {
      // A cancel that fails is not worth an error banner — the run either finished on its
      // own or the backend is gone, and both are already visible.
    }
    setPlaying(false);
  }, [run]);

  // --- collecting ---------------------------------------------------------------
  useEffect(() => {
    if (!run || run.state === 'complete' || run.state === 'failed') return;

    const controller = new AbortController();
    const timer = window.setInterval(() => {
      void pollRun(run.job_id, collected.current, run.start + run.total, controller.signal)
        .then((next) => {
          if (controller.signal.aborted) return;
          setByFrame((current) => merge(current, next.frames, run.start));
          collected.current = Math.max(collected.current, highest(next.frames) + 1);
          setRun(next);
        })
        .catch(() => undefined);
    }, POLL_MS);

    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [run]);

  // --- playing ------------------------------------------------------------------
  useEffect(() => {
    if (!playing || !run) return;

    const timer = window.setInterval(
      () =>
        setIndex((current) => {
          const next = current + 1;
          // Stops at the last *analysed* frame rather than wrapping. Wrapping mid-run
          // would look like the video restarting on its own.
          if (next >= run.total) {
            setPlaying(false);
            return current;
          }
          return next;
        }),
      Math.max(1000 / Math.max(fps, 1), 16),
    );
    return () => window.clearInterval(timer);
  }, [playing, run, fps]);

  return {
    run,
    error,
    byFrame,
    index,
    playing,
    start,
    stop,
    setIndex,
    setPlaying,
    clear,
  };
}

/** Absolute frame index → predictions, folded into what is already held. */
function merge(
  current: ReadonlyMap<number, readonly Prediction[]>,
  frames: readonly FramePredictions[],
  start: number,
): ReadonlyMap<number, readonly Prediction[]> {
  if (frames.length === 0) return current;
  const next = new Map(current);
  for (const frame of frames) {
    // `frame.index` is absolute in the source; the player counts from the run's start, so
    // this is where the two coordinate systems meet. Getting it wrong shows frame 0's
    // boxes over frame 200's picture, which reads as a broken model.
    next.set(frame.index - start, frame.predictions);
  }
  return next;
}

function highest(frames: readonly FramePredictions[]): number {
  return frames.reduce((best, frame) => Math.max(best, frame.index), -1);
}
