/**
 * Inspect datasets (doc 74): open a dataset and play its videos, folders and loose images
 * back with every stored annotation drawn on.
 */

import { useEffect, useMemo, useState, type JSX } from 'react';

import { listDatasets, type DatasetInfo } from '../api/datasets';
import type { SequenceFrame } from '../api/datasetSequences';
import { sequenceLabel } from '../api/datasetSequences';
import { probeSequence } from '../api/video';
import { AnnotationViewToggle } from '../components/AnnotationViewToggle';
import { DatasetPlayer } from '../components/DatasetPlayer';
import { useInspectData } from '../hooks/useInspectData';
import { usePersistentState } from '../hooks/usePersistentState';
import { usePlayback } from '../hooks/usePlayback';
import { looksLikeVideo } from '../lib/imageSource';
import { isAnnotationView, isString, stillListed } from '../lib/persisted';
import { DEFAULT_VIEW, type AnnotationView } from '../types/annotationView';
import type { InspectRequest } from '../types/navigation';

interface Track {
  readonly key: string;
  readonly label: string;
  readonly frames: readonly SequenceFrame[];
}

const LOOSE = '__loose__';
/** For a folder or loose images, which have no rate of their own. */
const STILLS_FPS = 4;

/** Every Nth frame was kept, so the saved frames play at the video's rate divided by N. */
function playbackFps(sourceFps: number | null, frames: readonly SequenceFrame[]): number {
  if (!sourceFps || frames.length < 2) return STILLS_FPS;
  const gaps = frames.slice(1).map((frame, i) => frame.index - frames[i]!.index);
  const gap = gaps.sort((a, b) => a - b)[Math.floor(gaps.length / 2)] ?? 1;
  return Math.max(0.5, Math.round((sourceFps / Math.max(1, gap)) * 2) / 2);
}

export function InspectTab({ request }: { readonly request: InspectRequest | null }): JSX.Element {
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [datasetChoice, setDatasetChoice] = usePersistentState('inspect.dataset', '', isString);
  const [trackChoice, setTrackChoice] = useState('');
  const [view, setView] = usePersistentState<AnnotationView>('inspect.view', DEFAULT_VIEW, isAnnotationView);

  useEffect(() => {
    const controller = new AbortController();
    listDatasets(controller.signal)
      .then(setDatasets)
      .catch(() => setDatasets([]));
    return () => controller.abort();
  }, []);

  // A jump from the Generator is an explicit instruction, not a default: it wins over
  // whatever was remembered, and a second press of the same button applies again.
  useEffect(() => {
    if (!request) return;
    setDatasetChoice(request.datasetId);
    setTrackChoice(request.sequence ?? '');
  }, [request, setDatasetChoice]);

  const withImages = datasets.filter((entry) => entry.counts.images > 0);
  const datasetId =
    stillListed(datasetChoice, datasets.map((entry) => entry.id)) || withImages[0]?.id || '';
  const hasMasks = (datasets.find((entry) => entry.id === datasetId)?.counts.masks ?? 0) > 0;
  const data = useInspectData(datasetId);

  const tracks: readonly Track[] = useMemo(() => {
    if (!data.sequences) return [];
    const found = data.sequences.sequences.map((sequence) => ({
      key: sequence.source,
      label: sequenceLabel(sequence),
      frames: sequence.frames,
    }));
    const loose = data.sequences.loose;
    return loose.length > 0
      ? [...found, { key: LOOSE, label: `Images not in a sequence · ${loose.length}`, frames: loose }]
      : found;
  }, [data.sequences]);
  const track = tracks.find((entry) => entry.key === trackChoice) ?? tracks[0] ?? null;

  const [sourceFps, setSourceFps] = useState<number | null>(null);
  useEffect(() => {
    setSourceFps(null);
    if (!track || !looksLikeVideo(track.key)) return;
    const controller = new AbortController();
    probeSequence(track.key, controller.signal)
      .then((info) => setSourceFps(info.fps))
      .catch(() => undefined); // moved since: the stills rate is a fine fallback
    return () => controller.abort();
  }, [track]);

  const frames = track?.frames ?? [];
  const playback = usePlayback(frames.length, playbackFps(sourceFps, frames), `${datasetId}:${track?.key ?? ''}`);

  return (
    <section className="studio">
      <h2 className="studio__title">Inspect datasets</h2>
      <p className="studio__lead">
        Play a dataset back with what it holds drawn on — a video, a folder, or its loose images.
      </p>

      <div className="inspect__pickers">
        <label className="genpanel__field">
          <span>Dataset</span>
          <select value={datasetId} onChange={(event) => setDatasetChoice(event.target.value)}>
            {datasets.length === 0 && <option value="">No datasets yet</option>}
            {datasets.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name} ({entry.counts.images} images)
              </option>
            ))}
          </select>
        </label>
        {tracks.length > 1 && (
          <label className="genpanel__field">
            <span>Play</span>
            <select value={track?.key ?? ''} onChange={(event) => setTrackChoice(event.target.value)}>
              {tracks.map((entry) => (
                <option key={entry.key} value={entry.key}>
                  {entry.label}
                </option>
              ))}
            </select>
          </label>
        )}
        {hasMasks && (
          <AnnotationViewToggle view={view} onChange={setView} hasMasks hasBoxes groupName="inspect-view" />
        )}
      </div>

      {data.loading && <p role="status">Loading the dataset…</p>}
      {data.error && (
        <p className="admin__error" role="alert">
          {data.error}
        </p>
      )}
      {!data.loading && datasetId && tracks.length === 0 && !data.error && (
        <p role="status">This dataset has no images yet.</p>
      )}

      {track && data.sequences && (
        <DatasetPlayer
          datasetId={datasetId}
          trackKey={track.key}
          frames={frames}
          images={data.images}
          classNames={data.sequences.class_names}
          hasMasks={hasMasks}
          view={view}
          playback={playback}
        />
      )}
    </section>
  );
}
