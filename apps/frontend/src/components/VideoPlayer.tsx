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

import { useMemo, type JSX } from 'react';

import { FrameCanvas } from './FrameCanvas';
import type { RenderedImage } from '../lib/geometry';
import { estimateSeconds, type SequenceInfo } from '../api/video';
import type { SequenceRunState } from '../hooks/useSequenceRun';
import { useT, type Translator } from '../i18n';

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

/** The estimate in words — `describeEstimate`'s thresholds, in the viewer's language. */
function describeTime(seconds: number, t: Translator['t']): string {
  if (seconds < 1) return t('run.player.estimateMoment');
  if (seconds < 90) return t('run.player.estimateSeconds', { value: Math.round(seconds) });
  if (seconds < 3600) return t('run.player.estimateMinutes', { value: Math.round(seconds / 60) });
  return t('run.player.estimateHours', { value: (seconds / 3600).toFixed(1) });
}

/** A sentence with `{count}` in bold: split around the placeholder, which `t` leaves in. */
function withBoldCount(sentence: string, count: number): JSX.Element {
  const [before = '', after = ''] = sentence.split('{count}');
  return (
    <>
      {before}
      <strong>{count}</strong>
      {after}
    </>
  );
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
  const { t, tp } = useT();
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
  const analysedCount = run?.total ?? 0;
  const runStart = run?.start ?? start;

  // Clamped the way the backend clamps it, so the estimate describes the run that will
  // actually happen rather than the one that was typed.
  const planned = Math.max(0, Math.min(count, info.frames - start));
  const estimate = useMemo(
    () => estimateSeconds(planned, foundationIds, headCount),
    [planned, foundationIds, headCount],
  );

  const absolute = runStart + index;
  const nothingSelected = foundationIds.length === 0 && headCount === 0;

  return (
    <section className="player">
      <div className="player__range">
        <label className="player__field">
          <span>{t('run.player.startAt')}</span>
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
          <span>{t('run.player.howMany')}</span>
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
          <span>{t('run.player.playAt')}</span>
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
        {info.kind === 'video' ? t('run.player.kindVideo') : t('run.player.kindFolder')} ·{' '}
        {tp('run.player.frames', info.frames)}
        {info.fps
          ? ` · ${info.fps.toFixed(1)} fps · ${(info.frames / info.fps).toFixed(1)}s`
          : ''}
        {planned > 0 && (
          <>
            {' — '}
            {withBoldCount(t('run.player.analysing', { time: describeTime(estimate, t) }), planned)}
            <span className="player__hint"> {t('run.player.estimateNote')}</span>
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
          {run?.state === 'running'
            ? t('run.player.analysingButton')
            : tp('run.player.analyse', planned)}
        </button>

        {run?.state === 'running' && (
          <button type="button" className="btn btn--small" onClick={() => void state.stop()}>
            {t('run.player.stop')}
          </button>
        )}

        {nothingSelected && (
          <span className="player__hint">{t('run.player.pickModel')}</span>
        )}
      </div>

      {state.error && <p role="alert" className="player__error">{state.error}</p>}

      {run && (
        <>
          <p role="status" className="player__progress">
            {run.state === 'running'
              ? t('run.player.progress', { done: run.done, total: run.total })
              : t(run.state === 'cancelled' ? 'run.player.stopped' : 'run.player.ready', {
                  done: byFrame.size,
                  total: run.total,
                })}
            {run.unreadable > 0 && ` · ${t('run.player.unreadable', { count: run.unreadable })}`}
          </p>

          <FrameCanvas
            source={info.source}
            index={index}
            runStart={runStart}
            frames={analysedCount}
            naturalWidth={info.width}
            naturalHeight={info.height}
            generation={run.job_id}
            label={t('run.player.frameLabel', { index: absolute })}
            renderOverlay={(geometry) => renderOverlay(index, geometry)}
          />

          <div className="player__transport">
            <button
              type="button"
              className="btn btn--small"
              onClick={() => state.setPlaying(!playing)}
              disabled={byFrame.size === 0}
            >
              {playing ? t('run.player.pause') : t('run.player.play')}
            </button>
            <input
              className="player__scrub"
              type="range"
              min={0}
              max={Math.max(0, analysedCount - 1)}
              value={index}
              aria-label={t('run.player.slider')}
              onChange={(event) => {
                state.setPlaying(false);
                state.setIndex(Number(event.target.value));
              }}
            />
            <span className="player__counter">
              {t('run.player.counter', { index: absolute })}
              {info.fps ? ` · ${(absolute / info.fps).toFixed(1)}s` : ''}
              {/* Says so rather than showing a bare frame: an un-analysed frame with no
                  overlay is otherwise indistinguishable from one where nothing was found. */}
              {!byFrame.has(index) && <span className="player__hint"> · {t('run.player.notAnalysed')}</span>}
            </span>
          </div>
        </>
      )}
    </section>
  );
}
