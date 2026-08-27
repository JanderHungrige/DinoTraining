/**
 * Watching a frame sequence with its annotations (doc 68).
 *
 * Three states, in order, and each only offers what makes sense in it: choose a range,
 * watch it being analysed, then play it. They are one component because they are one
 * task — a wizard would make the range unreachable once a run had started, and adjusting
 * the range after seeing the first result is the normal thing to do.
 *
 * **The frame is an `<img>`, not a `<video>`.** A video element gives no exact frame index
 * and drops frames under load, so the picture and the prediction drawn over it would be
 * different frames and every box would trail its object. Doc 68 exists to prevent exactly
 * that.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type JSX } from 'react';

import { fitContain, type RenderedImage } from '../lib/geometry';

import { describeEstimate, estimateSeconds, frameUrl, type SequenceInfo } from '../api/video';
import type { SequenceRunState } from '../hooks/useSequenceRun';

export interface VideoPlayerProps {
  readonly info: SequenceInfo;
  readonly state: SequenceRunState;
  readonly start: number;
  readonly count: number;
  readonly fps: number;
  readonly onStartChange: (start: number) => void;
  readonly onCountChange: (count: number) => void;
  readonly onFpsChange: (fps: number) => void;
  readonly onRun: () => void;
  readonly foundationIds: readonly string[];
  readonly headCount: number;
  /** Draws the overlays for the frame on screen. Owned by the tab, which knows the view.
   *
   *  Takes the **measured** geometry rather than the natural size: the frame is letterboxed
   *  into whatever space the stage has, and overlays placed in natural coordinates over a
   *  CSS-scaled image are wrong by the scale factor and offset by the letterbox — every box
   *  in the wrong place, which reads as a broken model rather than a layout bug. */
  readonly renderOverlay: (index: number, rendered: RenderedImage) => JSX.Element | null;
}

/** Seconds, when the source has a rate to convert with. */
function asTime(frames: number, fps: number | null): string {
  return fps ? `${(frames / fps).toFixed(1)}s` : `${frames} frames`;
}

export function VideoPlayer({
  info,
  state,
  start,
  count,
  fps,
  onStartChange,
  onCountChange,
  onFpsChange,
  onRun,
  foundationIds,
  headCount,
  renderOverlay,
}: VideoPlayerProps): JSX.Element {
  const { run, byFrame, index, playing } = state;

  // The stage is measured, not assumed: the frame is letterboxed into whatever space it
  // has, and an overlay placed in natural coordinates over a scaled image is wrong by the
  // scale and offset by the letterbox.
  //
  // **A callback ref, not a `useRef` plus an effect.** The stage only exists once a run
  // does, so an effect that reads `ref.current` on mount finds `null`, returns early, and
  // never observes anything — the measurement then stays at its 0x0 initial value and
  // every box collapses to a point in the corner. Found exactly that way, live. A callback
  // ref fires when the node actually attaches, which is the moment there is something to
  // measure.
  const stageRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const [rendered, setRendered] = useState<RenderedImage>({
    width: 0,
    height: 0,
    offsetX: 0,
    offsetY: 0,
    naturalWidth: info.width,
    naturalHeight: info.height,
  });

  const measure = useCallback((): void => {
    const node = stageRef.current;
    if (!node) return;
    const box = node.getBoundingClientRect();
    setRendered(fitContain(box.width, box.height, info.width, info.height));
  }, [info.width, info.height]);

  const attachStage = useCallback(
    (node: HTMLDivElement | null): void => {
      observerRef.current?.disconnect();
      stageRef.current = node;
      if (!node) return;
      measure();
      if (typeof ResizeObserver === 'undefined') return;
      const observer = new ResizeObserver(() => measure());
      observer.observe(node);
      observerRef.current = observer;
    },
    [measure],
  );

  // The source can change under a mounted stage — a different video, a different size —
  // and the letterbox with it.
  useEffect(() => measure(), [measure]);
  useEffect(() => () => observerRef.current?.disconnect(), []);

  // Clamped the way the backend clamps it, so the estimate describes the run that will
  // actually happen rather than the one that was typed.
  const planned = Math.max(0, Math.min(count, info.frames - start));
  const estimate = useMemo(
    () => estimateSeconds(planned, foundationIds, headCount),
    [planned, foundationIds, headCount],
  );

  const analysed = run?.total ?? 0;
  const absolute = (run?.start ?? start) + index;
  const nothingSelected = foundationIds.length === 0 && headCount === 0;

  return (
    <section className="player">
      <div className="player__range">
        <label className="player__field">
          <span>Start at frame</span>
          <input
            type="number"
            min={0}
            max={Math.max(0, info.frames - 1)}
            value={start}
            disabled={run?.state === 'running'}
            onChange={(event) => onStartChange(Number(event.target.value))}
          />
        </label>
        <label className="player__field">
          <span>How many frames</span>
          <input
            type="number"
            min={1}
            max={5000}
            value={count}
            disabled={run?.state === 'running'}
            onChange={(event) => onCountChange(Number(event.target.value))}
          />
        </label>
        <label className="player__field">
          <span>Play at (fps)</span>
          <input
            type="number"
            min={1}
            max={60}
            value={fps}
            onChange={(event) => onFpsChange(Number(event.target.value))}
          />
        </label>
      </div>

      {/* Said before the click, not after — it is the number that changes the decision.
          Someone who sees four minutes picks a shorter range instead of cancelling three
          minutes in. */}
      <p className="player__estimate">
        {info.kind === 'video' ? 'Video' : 'Folder'} · {info.frames} frames
        {info.fps ? ` · ${info.fps.toFixed(1)} fps · ${asTime(info.frames, info.fps)}` : ''}
        {planned > 0 && (
          <>
            {' — '}
            analysing <strong>{planned}</strong> of them takes {describeEstimate(estimate)}
            <span className="player__hint"> (an estimate)</span>
          </>
        )}
      </p>

      <div className="player__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={run?.state === 'running' || planned < 1 || nothingSelected}
          onClick={onRun}
        >
          {run?.state === 'running' ? 'Analysing…' : `Analyse ${planned} frame${planned === 1 ? '' : 's'}`}
        </button>

        {run?.state === 'running' && (
          <button type="button" className="btn btn--small" onClick={() => void state.stop()}>
            Stop
          </button>
        )}

        {nothingSelected && (
          <span className="player__hint">Pick at least one head or foundation model above.</span>
        )}
      </div>

      {state.error && <p role="alert" className="player__error">{state.error}</p>}

      {run && (
        <>
          <p role="status" className="player__progress">
            {run.state === 'running'
              ? `Analysed ${run.done} of ${run.total} frames…`
              : `${run.state === 'cancelled' ? 'Stopped' : 'Ready'} — ${byFrame.size} of ${run.total} frames analysed`}
            {run.unreadable > 0 && ` · ${run.unreadable} could not be read`}
          </p>

          <div className="player__stage" ref={attachStage}>
            <img
              className="player__frame"
              src={frameUrl(info.source, absolute)}
              alt={`Frame ${absolute}`}
              draggable={false}
              onLoad={measure}
            />
            <div className="overlay">{renderOverlay(index, rendered)}</div>
          </div>

          <div className="player__transport">
            <button
              type="button"
              className="btn btn--small"
              onClick={() => state.setPlaying(!playing)}
              disabled={byFrame.size === 0}
            >
              {playing ? 'Pause' : 'Play'}
            </button>
            <input
              className="player__scrub"
              type="range"
              min={0}
              max={Math.max(0, analysed - 1)}
              value={index}
              aria-label="Frame"
              onChange={(event) => {
                state.setPlaying(false);
                state.setIndex(Number(event.target.value));
              }}
            />
            <span className="player__counter">
              frame {absolute}
              {info.fps ? ` · ${(absolute / info.fps).toFixed(1)}s` : ''}
              {/* Says so rather than showing a bare frame: an un-analysed frame with no
                  overlay is otherwise indistinguishable from one where nothing was found. */}
              {!byFrame.has(index) && <span className="player__hint"> · not analysed</span>}
            </span>
          </div>
        </>
      )}
    </section>
  );
}
