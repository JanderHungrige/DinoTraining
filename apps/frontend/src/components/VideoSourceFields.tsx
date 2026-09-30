/**
 * A video as the Dataset Generator's source (doc 73): which file, and which of its frames.
 *
 * The frames are decoded into the destination dataset before the session starts, so the
 * cost is stated before the click: how many frames, and roughly how much disk. A 10-minute
 * clip at 30 fps is 18,000 frames and several gigabytes, which nobody should discover by
 * pressing Start.
 */

import { useEffect, useState, type JSX } from 'react';

import { probeSequence, type SequenceInfo } from '../api/video';
import { useT } from '../i18n';
import { hasNativeDialog, pickVideoFile } from '../lib/dialog';
import { looksLikeVideo } from '../lib/imageSource';
import type { VideoRange } from './ImageSourceField';

export interface VideoSourceFieldsProps {
  readonly id: string;
  readonly path: string;
  readonly range: VideoRange;
  readonly disabled: boolean;
  readonly onChange: (path: string, range: VideoRange) => void;
}

/** JPEG at quality 92 over camera footage: roughly 0.2 bytes a pixel. Stated as an estimate. */
const BYTES_PER_PIXEL = 0.2;

/** How many frames the range will actually give, from what the video holds. */
export function framesInRange(total: number, range: VideoRange): number {
  if (range.start >= total || range.stride < 1) return 0;
  return Math.min(range.count, Math.ceil((total - range.start) / range.stride));
}

export function estimateMegabytes(info: SequenceInfo, frames: number): number {
  return Math.max(1, Math.round((frames * info.width * info.height * BYTES_PER_PIXEL) / 1e6));
}

function whole(value: string, fallback: number, minimum: number): number {
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? Math.max(minimum, parsed) : fallback;
}

export function VideoSourceFields({
  id,
  path,
  range,
  disabled,
  onChange,
}: VideoSourceFieldsProps): JSX.Element {
  const { t } = useT();
  const [info, setInfo] = useState<SequenceInfo | null>(null);
  const [probeError, setProbeError] = useState<string | null>(null);
  const [hasPicker, setHasPicker] = useState(false);
  useEffect(() => setHasPicker(hasNativeDialog()), []);

  useEffect(() => {
    setInfo(null);
    setProbeError(null);
    if (!looksLikeVideo(path)) return;
    const controller = new AbortController();
    // Debounced: the probe opens the file, and typing a path opens it once per keystroke.
    const timer = setTimeout(() => {
      probeSequence(path, controller.signal)
        .then(setInfo)
        .catch(() => {
          if (!controller.signal.aborted) setProbeError(t('studio.video.probeError'));
        });
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [path]);

  const frames = info ? framesInRange(info.frames, range) : 0;
  const set = (patch: Partial<VideoRange>): void => onChange(path, { ...range, ...patch });

  return (
    <div className="videosrc">
      <label className="genpanel__field" htmlFor={`${id}-video`}>
        {t('studio.video.file')}
        <span className="setup__control">
          <input
            id={`${id}-video`}
            type="text"
            value={path}
            placeholder="/Users/you/rides/track.mp4"
            disabled={disabled}
            onChange={(event) => onChange(event.target.value, range)}
          />
          {hasPicker && (
            <button
              type="button"
              className="btn"
              disabled={disabled}
              onClick={() => void pickVideoFile().then((picked) => picked && onChange(picked, range))}
            >
              {t('studio.video.pick')}
            </button>
          )}
        </span>
      </label>

      {path.trim() !== '' && !looksLikeVideo(path) && (
        <p className="srcfield__hint">
          {t('studio.video.notVideo')}
        </p>
      )}
      {probeError && (
        <p className="admin__error" role="alert">
          {probeError}
        </p>
      )}

      <VideoRangeInputs range={range} disabled={disabled} onChange={set} />

      {info && (
        <p className="srcfield__hint" role="status">
          {t('studio.video.frames', { frames: info.frames.toLocaleString() })}
          {info.fps ? ` ${t('studio.video.fps', { fps: Math.round(info.fps) })}` : ''} · {info.width}×{info.height}.{' '}
          {frames === 0
            ? t('studio.video.pastEnd')
            : t('studio.video.decodes', {
                frames: frames.toLocaleString(),
                mb: estimateMegabytes(info, frames).toLocaleString(),
              })}
        </p>
      )}
    </div>
  );
}

function VideoRangeInputs({
  range,
  disabled,
  onChange: set,
}: {
  readonly range: VideoRange;
  readonly disabled: boolean;
  readonly onChange: (patch: Partial<VideoRange>) => void;
}): JSX.Element {
  const { t } = useT();
  return (
    <div className="videosrc__range">
      <label>
        {t('studio.video.from')}
        <input
          type="number"
          min={0}
          value={range.start}
          disabled={disabled}
          onChange={(event) => set({ start: whole(event.target.value, range.start, 0) })}
        />
      </label>
      <label>
        {t('studio.video.count')}
        <input
          type="number"
          min={1}
          value={range.count}
          disabled={disabled}
          onChange={(event) => set({ count: whole(event.target.value, range.count, 1) })}
        />
      </label>
      <label>
        {t('studio.video.every')}
        <input
          type="number"
          min={1}
          value={range.stride}
          disabled={disabled}
          aria-label={t('studio.video.everyAria')}
          onChange={(event) => set({ stride: whole(event.target.value, range.stride, 1) })}
        />
        {t('studio.video.th')}
      </label>
    </div>
  );
}
