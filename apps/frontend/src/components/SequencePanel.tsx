/**
 * The Inference Viewer's video half, wired up (doc 68).
 *
 * Extracted from `InferenceViewerTab` when the two halves together crossed the project's
 * 300-line gate. The seam is real rather than arbitrary: everything here is about a
 * *sequence* — probing it, ranging it, running it, playing it — and everything left in the
 * tab is about a single image. They share only the model selection, which arrives as props.
 *
 * This component owns the probe, so the tab never has to ask what a path turns out to be.
 */

import { useEffect, useMemo, useRef, useState, type JSX } from 'react';

import { usePersistentState } from '../hooks/usePersistentState';
import { isNumber } from '../lib/persisted';

import { DEFAULT_FPS, probeSequence, type SequenceInfo } from '../api/video';
import { renderOverlayFor } from './overlays/registry';
import { useSequenceRun } from '../hooks/useSequenceRun';
import { VideoPlayer } from './VideoPlayer';
import { useT } from '../i18n';
import type { AnnotationView } from '../types/annotationView';
import type { RenderedImage } from '../lib/geometry';
import type { Prediction } from '../api/inference';

/** Doc 68's default range: enough to see motion, short enough to wait for. */
const DEFAULT_COUNT = 60;

export interface SequencePanelProps {
  readonly path: string | null;
  readonly view: AnnotationView;
  readonly foundationIds: readonly string[];
  readonly instanceIds: readonly string[];
  readonly backboneId: string;
  readonly concept: string;
  /** 2026-10-02: a single picture in this mode showed nothing at all; this opens it in the
   *  single-image view instead. */
  readonly onOpenAsImage?: () => void;
  /** 2026-10-21 (Jan): one Run button, the viewer's "Run models". Each increment starts an
   *  analysis here; `onReadyChange` says whether one can start. */
  readonly runRequest?: number;
  readonly onReadyChange?: (ready: boolean) => void;
}

export function SequencePanel({
  path,
  view,
  foundationIds,
  instanceIds,
  backboneId,
  concept,
  onOpenAsImage,
  runRequest = 0,
  onReadyChange,
}: SequencePanelProps): JSX.Element | null {
  const { t } = useT();
  // `null` until the path turns out to be something playable. A single image is not.
  const [sequence, setSequence] = useState<SequenceInfo | null>(null);
  const [start, setStart] = useState(0);
  // Remembered (doc 69). `start` is not: it belongs to one clip, and `fps` is re-read
  // from each clip on probe anyway.
  const [count, setCount] = usePersistentState('viewer.sequence.count', DEFAULT_COUNT, isNumber);
  const [fps, setFps] = useState(DEFAULT_FPS);
  const playback = useSequenceRun(fps);
  const planned = sequence ? Math.max(0, Math.min(count, sequence.frames - start)) : 0;
  const panes = useMemo(() => modelPanes(playback.byFrame), [playback.byFrame]);
  const ready = Boolean(sequence && sequence.frames >= 2 && planned >= 1 && playback.run?.state !== 'running');
  useEffect(() => onReadyChange?.(ready), [ready, onReadyChange]);
  const analyse = (): void => {
    if (!sequence) return;
    void playback.start({
      source: sequence.source,
      start,
      count,
      backboneId,
      instanceIds,
      foundationIds,
      concept,
      scoreThreshold: 0.3,
    });
  };
  // Only a new request starts a run: not the first render, not a re-render.
  const handled = useRef(runRequest);
  useEffect(() => {
    if (runRequest === handled.current) return;
    handled.current = runRequest;
    if (ready) analyse();
  }, [runRequest]);

  useEffect(() => {
    if (!path) {
      setSequence(null);
      return;
    }
    const controller = new AbortController();
    void probeSequence(path, controller.signal)
      .then((info) => {
        if (controller.signal.aborted) return;
        setSequence(info);
        // A folder has no rate of its own, so the player counts at its own default rather
        // than at a number invented for the folder.
        setFps(Math.round(info.fps ?? DEFAULT_FPS));
      })
      // Not an error: a single image probes as unplayable, which is simply the answer.
      .catch(() => setSequence(null));
    return () => controller.abort();
  }, [path]);

  if (!path) {
    return (
      <p role="status" className="player__hint">
        {t('run.sequence.pickSource')}
      </p>
    );
  }

  if (!sequence || sequence.frames < 2) {
    return (
      <p role="status" className="player__hint">
        {t('run.sequence.notSequence')}{' '}
        {onOpenAsImage && (
          <button type="button" className="btn btn--small" onClick={onOpenAsImage}>
            {t('run.sequence.openAsImage')}
          </button>
        )}
      </p>
    );
  }

  return (
    <VideoPlayer
      info={sequence}
      state={playback}
      start={start}
      count={count}
      fps={fps}
      onStartChange={setStart}
      onCountChange={setCount}
      onFpsChange={setFps}
      foundationIds={foundationIds}
      headCount={instanceIds.length}
      panes={panes}
      renderOverlay={(index: number, rendered: RenderedImage, paneKey: string) => {
        const frame = playback.byFrame.get(index);
        if (!frame || frame.length === 0) return null;
        // One pane per model, side by side like the single-image view (2026-10-21, Jan:
        // stacked on one frame they could not be compared). An empty key is the single
        // pane, which shows every prediction.
        const shown = paneKey === '' ? frame : frame.filter((p) => p.instance_id === paneKey);
        return (
          <>
            {shown.map((prediction) => (
              <div key={prediction.instance_id} className="overlay">
                {renderOverlayFor(prediction, rendered, view)}
              </div>
            ))}
          </>
        );
      }}
    />
  );
}

/** The models in a run, in the order they first answer: each one a pane. */
export function modelPanes(
  byFrame: ReadonlyMap<number, readonly Prediction[]>,
): readonly { readonly key: string; readonly label: string }[] {
  const seen = new Map<string, string>();
  for (const frame of byFrame.values()) {
    for (const prediction of frame) {
      if (!seen.has(prediction.instance_id)) seen.set(prediction.instance_id, prediction.head_name);
    }
  }
  return [...seen].map(([key, label]) => ({ key, label }));
}
