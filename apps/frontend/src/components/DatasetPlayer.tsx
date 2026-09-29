/**
 * Plays one track of a dataset (a video, a folder, or its loose images) with the stored
 * annotations drawn over each frame (doc 74).
 *
 * The picture is doc 68's `FrameCanvas`, painted from a cache ahead of the clock, with
 * its URLs pointed at the dataset's own files instead of the video route.
 */

import { useCallback, type JSX, type ReactNode } from 'react';

import { imageUrl } from '../api/annotate';
import type { DatasetImageInfo } from '../api/datasets';
import type { SequenceFrame } from '../api/datasetSequences';
import { useFrameMasks } from '../hooks/useFrameMasks';
import type { Playback } from '../hooks/usePlayback';
import type { AnnotationView } from '../types/annotationView';
import { FrameCanvas } from './FrameCanvas';
import { StoredOverlay } from './StoredOverlay';

export interface DatasetPlayerProps {
  readonly datasetId: string;
  readonly trackKey: string;
  readonly frames: readonly SequenceFrame[];
  readonly images: ReadonlyMap<string, DatasetImageInfo>;
  readonly classNames: readonly string[];
  readonly hasMasks: boolean;
  readonly view: AnnotationView;
  readonly playback: Playback;
  /** Doc 75's timeline goes here, under the controls. */
  readonly children?: ReactNode;
}

/** Frames on disk that were never saved have no stored size; a saved neighbour's is right
 *  for a video (every frame is the same size) and harmless otherwise (nothing to draw). */
function sizeOf(
  frames: readonly SequenceFrame[],
  index: number,
  images: ReadonlyMap<string, DatasetImageInfo>,
): { width: number; height: number } {
  const own = frames[index] ? images.get(frames[index].path) : undefined;
  const any = own ?? frames.map((frame) => images.get(frame.path)).find(Boolean);
  return { width: any?.width ?? 640, height: any?.height ?? 480 };
}

export function DatasetPlayer({
  datasetId,
  trackKey,
  frames,
  images,
  classNames,
  hasMasks,
  view,
  playback,
  children,
}: DatasetPlayerProps): JSX.Element {
  const { index, playing, fps } = playback;
  const frame = frames[index];
  const masks = useFrameMasks(datasetId, frames, index, hasMasks);
  const { width, height } = sizeOf(frames, index, images);
  const urlFor = useCallback((i: number) => imageUrl(frames[i]?.path ?? ''), [frames]);
  const stored = frame ? images.get(frame.path) : undefined;

  return (
    <div className="player">
      <FrameCanvas
        source={trackKey}
        index={index}
        runStart={0}
        frames={frames.length}
        naturalWidth={width}
        naturalHeight={height}
        generation={`${datasetId}:${trackKey}`}
        label={frame ? `Frame ${frame.index}` : 'No frame'}
        urlFor={urlFor}
        renderOverlay={(rendered) => (
          <StoredOverlay
            boxes={stored?.boxes ?? []}
            masks={masks}
            classNames={classNames}
            width={width}
            height={height}
            rendered={rendered}
            view={view}
          />
        )}
      />

      <div className="player__transport" role="group" aria-label="Playback">
        <button type="button" className="btn" onClick={() => playback.step(-1)} disabled={index === 0}>
          ◀ Frame
        </button>
        <button type="button" className="btn btn--primary" onClick={playback.toggle}>
          {playing ? '❚❚ Pause' : '▶ Play'}
        </button>
        <button
          type="button"
          className="btn"
          onClick={() => playback.step(1)}
          disabled={index >= frames.length - 1}
        >
          Frame ▶
        </button>
        <input
          type="range"
          className="player__scrub"
          min={0}
          max={Math.max(0, frames.length - 1)}
          value={index}
          aria-label="Position in the sequence"
          onChange={(event) => playback.setIndex(Number(event.target.value))}
        />
        <span className="player__counter" role="status">
          {frames.length === 0 ? '—' : `${index + 1} / ${frames.length}`}
          {frame ? ` · frame ${frame.index}` : ''}
          {frame && !frame.annotated ? ' · not annotated' : ''}
        </span>
        <label className="player__fps">
          <input
            type="number"
            min={0.5}
            max={60}
            step={0.5}
            value={fps}
            onChange={(event) => playback.setFps(Number(event.target.value) || fps)}
          />
          fps
        </label>
      </div>

      {children}
    </div>
  );
}
