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

import { useEffect, useState, type JSX } from 'react';

import { DEFAULT_FPS, probeSequence, type SequenceInfo } from '../api/video';
import { renderOverlayFor } from './overlays/registry';
import { useSequenceRun } from '../hooks/useSequenceRun';
import { VideoPlayer } from './VideoPlayer';
import type { AnnotationView } from '../types/annotationView';
import type { RenderedImage } from '../lib/geometry';

/** Doc 68's default range: enough to see motion, short enough to wait for. */
const DEFAULT_COUNT = 60;

export interface SequencePanelProps {
  readonly path: string | null;
  readonly view: AnnotationView;
  readonly foundationIds: readonly string[];
  readonly instanceIds: readonly string[];
  readonly backboneId: string;
  readonly concept: string;
}

export function SequencePanel({
  path,
  view,
  foundationIds,
  instanceIds,
  backboneId,
  concept,
}: SequencePanelProps): JSX.Element | null {
  // `null` until the path turns out to be something playable. A single image is not.
  const [sequence, setSequence] = useState<SequenceInfo | null>(null);
  const [start, setStart] = useState(0);
  const [count, setCount] = useState(DEFAULT_COUNT);
  const [fps, setFps] = useState(DEFAULT_FPS);
  const playback = useSequenceRun(fps);

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
        Pick a folder of frames or a video file above.
      </p>
    );
  }

  if (!sequence || sequence.frames < 2) {
    return (
      <p role="status" className="player__hint">
        That path is not a sequence. Pick a folder of frames or a video file to play one.
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
      onRun={() =>
        void playback.start({
          source: sequence.source,
          start,
          count,
          backboneId,
          instanceIds,
          foundationIds,
          concept,
          scoreThreshold: 0.3,
        })
      }
      renderOverlay={(index: number, rendered: RenderedImage) => {
        const frame = playback.byFrame.get(index);
        if (!frame || frame.length === 0) return null;
        // Every prediction for the frame, stacked — the same thing the single-image panes
        // show side by side, which is what keeps the two surfaces agreeing.
        return (
          <>
            {frame.map((prediction) => (
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
