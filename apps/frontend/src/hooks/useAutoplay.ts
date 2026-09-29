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
  emptyProgress,
  runAutoplay,
  type AutoplayProgress,
  type AutoplayReport,
} from '../lib/autoplay';
import { proposeReview } from '../lib/generatorProposal';
import type { ImageReview } from '../lib/generatorSave';
import type { UnclearBand } from '../lib/unclearBand';
import { isBoolean } from '../lib/persisted';
import type { GeneratorConfig } from '../types/generatorConfig';
import type { GeneratorSession } from '../types/generatorSession';
import { usePersistentState } from './usePersistentState';

/** How long each proposal stays on screen before it is saved: long enough to see a wrong
 *  box and press Stop, short enough that a folder of 300 still moves. */
export const HOLD_MS = 500;

/** Autoplay is paused on an image, waiting for the user to judge in-band proposals. */
export interface AutoplayQuestion {
  readonly index: number;
  readonly count: number;
}

export interface Autoplay {
  readonly running: boolean;
  /** Doc 72: set while the run waits for an answer. */
  readonly question: AutoplayQuestion | null;
  /** Saves the image as it now stands on screen and carries on. */
  readonly answer: () => void;
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
  band: UnclearBand | null = null,
): Autoplay {
  const [running, setRunning] = useState(false);
  const [question, setQuestion] = useState<AutoplayQuestion | null>(null);
  // Resolves the pending question: the reviewed image, or null for Stop.
  const reply = useRef<((review: ImageReview | null) => void) | null>(null);
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
    setProgress(emptyProgress(Math.max(0, paths.length - start)));

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
      band,
      ask: (index, _review, count) =>
        new Promise<ImageReview | null>((resolve) => {
          reply.current = resolve;
          setQuestion({ index, count });
        }),
    }).then((result) => {
      controller.current = null;
      setRunning(false);
      setReport(result);
      // Hidden mode never moved the view. Land on the last image it worked on, so Stop
      // (or the end) leaves the user somewhere they can look and correct.
      if (hidden) live.current.goTo(result.lastIndex);
    });
  }, [config, hidden, band]);

  const settle = useCallback((review: ImageReview | null): void => {
    const resolve = reply.current;
    reply.current = null;
    setQuestion(null);
    resolve?.(review);
  }, []);

  const answer = useCallback((): void => settle(live.current.currentReview()), [settle]);

  const stop = useCallback((): void => {
    controller.current?.abort();
    // A run waiting on a question is parked on a promise the abort cannot reach.
    settle(null);
  }, [settle]);

  return { running, question, answer, hidden, setHidden, progress, report, play, stop };
}
