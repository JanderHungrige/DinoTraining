/**
 * Autoplay's React side (doc 71): starts and stops `runAutoplay`, and carries its progress
 * and final report to the screen.
 *
 * The run talks to the session through a ref to its *latest* render. Its callbacks (save,
 * show, goTo) are read at call time, not captured at Play, because the run outlives many
 * renders and a captured `save` would carry the state of the moment Play was pressed.
 *
 * Leaving the tab unmounts the Generator, and the run stops with it: there is no
 * background run to come back to. That is stated rather than hidden. Doc 69 keeps the
 * setup, and the images already saved are skipped when Play is pressed again.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  runAutoplay,
  type AutoplayProgress,
  type AutoplayReport,
} from '../lib/autoplay';
import { proposeReview } from '../lib/generatorProposal';
import { isBoolean } from '../lib/persisted';
import type { GeneratorConfig } from '../types/generatorConfig';
import type { GeneratorSession } from '../types/generatorSession';
import { usePersistentState } from './usePersistentState';

/** How long each proposal stays on screen before it is saved: long enough to see a wrong
 *  box and press Stop, short enough that a folder of 300 still moves. */
export const HOLD_MS = 500;

export interface Autoplay {
  readonly running: boolean;
  readonly hidden: boolean;
  readonly setHidden: (hidden: boolean) => void;
  readonly progress: AutoplayProgress | null;
  readonly report: AutoplayReport | null;
  readonly play: () => void;
  readonly stop: () => void;
}

export function useAutoplay(
  config: GeneratorConfig | null,
  session: GeneratorSession,
): Autoplay {
  const [running, setRunning] = useState(false);
  const [hidden, setHidden] = usePersistentState('generator.autoplayHidden', false, isBoolean);
  const [progress, setProgress] = useState<AutoplayProgress | null>(null);
  const [report, setReport] = useState<AutoplayReport | null>(null);
  const controller = useRef<AbortController | null>(null);
  const live = useRef(session);
  live.current = session;

  // Stop with the tab. A run left going against an unmounted component would keep
  // proposing and saving with nothing on screen to stop it.
  useEffect(() => () => controller.current?.abort(), []);

  const play = useCallback((): void => {
    if (!config || controller.current) return;
    const abort = new AbortController();
    controller.current = abort;
    const start = live.current.index;
    const paths = live.current.images;
    setRunning(true);
    setReport(null);
    // The total is known before the first image finishes; "0 of 0" would read as broken.
    setProgress({
      done: 0,
      total: Math.max(0, paths.length - start),
      saved: 0,
      empty: 0,
      failed: 0,
      skipped: 0,
    });

    void runAutoplay({
      paths,
      start,
      hidden,
      holdMs: HOLD_MS,
      signal: abort.signal,
      propose: (path) => proposeReview(config, path),
      save: (review) => live.current.save(review),
      isSaved: (path) => live.current.saved(path) !== undefined,
      show: (index, review) => {
        if (review === null) live.current.goTo(index);
        else live.current.show(review);
      },
      onProgress: setProgress,
    }).then((result) => {
      controller.current = null;
      setRunning(false);
      setReport(result);
      // Hidden mode never moved the view. Land on the last image it worked on, so Stop
      // (or the end) leaves the user somewhere they can look and correct.
      if (hidden) live.current.goTo(result.lastIndex);
    });
  }, [config, hidden]);

  const stop = useCallback((): void => controller.current?.abort(), []);

  return { running, hidden, setHidden, progress, report, play, stop };
}
