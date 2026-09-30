/**
 * Which images the Dataset Generator works through: the source's listing, narrowed by an
 * optional prescan filter (doc 53).
 *
 * Split out of `useGeneratorSession` when doc 71 needed room in it. The seam is real: this
 * answers "which images", the session answers "what happens on one of them".
 *
 * Doc 73: a video source is decoded into the destination dataset first, with progress, and
 * every image knows where it sits in its sequence, so a save can record it. A folder is a
 * sequence too, in its sorted order; a dataset source already carries its positions.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import type { FramePosition } from '../api/datasets';
import { extractFrames, type ExtractProgress } from '../api/videoExtract';
import { useT } from '../i18n';
import { resolveImageSource } from '../lib/imageSource';
import type { GeneratorConfig } from '../types/generatorConfig';

export interface GeneratorImages {
  /** The images to work through: all of them, or the prescan's hits. */
  readonly images: readonly string[];
  /** Every image the source holds, ignoring any prescan filter. */
  readonly allImages: readonly string[];
  readonly filtered: boolean;
  readonly setFilter: (paths: readonly string[] | null) => void;
  readonly loading: boolean;
  readonly listError: string | null;
  /** Doc 73: set while a video is being decoded into the dataset. */
  readonly decoding: ExtractProgress | null;
  /** Where an image sits in its sequence, or null for one that is not a frame. */
  readonly frameOf: (path: string) => FramePosition | null;
}

/** Lists or decodes the source; returns the image paths with their sequence positions. */
async function loadSource(
  config: GeneratorConfig,
  onDecoding: (progress: ExtractProgress) => void,
  signal: AbortSignal,
): Promise<{ paths: string[]; frames: Map<string, FramePosition> }> {
  const source = config.images;
  if (source.kind === 'video') {
    const decoded = await extractFrames(
      { source: source.path, datasetId: config.datasetId, ...source.range },
      onDecoding,
      signal,
    );
    const frames = new Map(
      decoded.map((frame) => [frame.path, { sequence: source.path, frame_index: frame.index }]),
    );
    return { paths: decoded.map((frame) => frame.path), frames };
  }
  const paths = await resolveImageSource(source, signal);
  const frames =
    source.kind === 'folder'
      ? new Map(paths.map((path, index) => [path, { sequence: source.folder, frame_index: index }]))
      : new Map<string, FramePosition>();
  return { paths, frames };
}

export function useGeneratorImages(config: GeneratorConfig | null): GeneratorImages {
  const [allImages, setAllImages] = useState<readonly string[]>([]);
  // A prescan's hits. Null means no filter. The full list stays loaded, so turning the
  // filter off costs nothing and re-reads nothing.
  const [filter, setFilter] = useState<readonly string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [decoding, setDecoding] = useState<ExtractProgress | null>(null);
  const [frames, setFrames] = useState<ReadonlyMap<string, FramePosition>>(new Map());
  // Read when a listing fails, not a reason to list again: a language switch must not
  // decode a video a second time.
  const tr = useT();
  const translate = useRef(tr);
  translate.current = tr;

  useEffect(() => {
    // Cleared before the new listing is asked for, not after it arrives (doc 50, bug 1).
    // A source that fails to load must not leave the previous one's images on screen: they
    // render fully interactive, so the user would review the old folder's pictures while
    // the boxes save into the newly chosen dataset.
    setAllImages([]);
    setFrames(new Map());
    setFilter(null);
    setListError(null);
    setDecoding(null);
    if (!config) return;

    const controller = new AbortController();
    setLoading(true);
    loadSource(config, setDecoding, controller.signal)
      .then(({ paths, frames: positions }) => {
        setAllImages(paths);
        setFrames(positions);
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setListError(
          caught instanceof ApiError || config.images.kind === 'video'
            ? (caught as Error).message
            : translate.current.t(
                config.images.kind === 'dataset'
                  ? 'generator.session.listFailedDataset'
                  : 'generator.session.listFailedFolder',
              ),
        );
      })
      .finally(() => {
        if (controller.signal.aborted) return;
        setLoading(false);
        setDecoding(null);
      });
    return () => controller.abort();
  }, [config]);

  const frameOf = useCallback((path: string) => frames.get(path) ?? null, [frames]);
  const kept = filter === null ? null : new Set(filter);
  const images = kept === null ? allImages : allImages.filter((path) => kept.has(path));

  return {
    images,
    allImages,
    filtered: filter !== null,
    setFilter,
    loading,
    listError,
    decoding,
    frameOf,
  };
}
