/**
 * Loading a session's images, from a folder or a dataset (doc 50).
 *
 * Split out of `useAnnotationSession` when that crossed 300 lines, and the seam is real:
 * everything here answers "what images are there, and what do they already have?", and
 * everything there is about moving between them and saving.
 *
 * The **existing boxes** are the reason this is not just a path list. Picking a dataset as
 * a source means "carry on working on this", so its boxes have to be on the canvas the
 * moment an image opens — and they arrive with the listing rather than one request per
 * image, which would put a round trip behind every press of the Next key.
 */

import { useEffect, useRef, useState } from 'react';

import { listFolderImages } from '../api/annotate';
import { listDatasetImages, storedToCanvasBoxes } from '../api/datasets';
import type { ImageSource } from '../components/ImageSourceField';
import type { CanvasBox } from '../types/annotation';

export interface SessionImages {
  readonly images: readonly string[];
  /** Boxes each image already carries. Empty for a folder source, which is what makes the
   *  two kinds behave identically everywhere downstream. */
  readonly existing: ReadonlyMap<string, readonly CanvasBox[]>;
  readonly error: string | null;
  /** Bumped on every completed load, so a consumer can reset its position exactly once. */
  readonly generation: number;
}

/** A stable key. Two sources of different kinds must never compare equal, or switching
 *  between them would not reload. */
function keyOf(source: ImageSource | null): string {
  if (source === null) return '';
  return source.kind === 'dataset' ? `dataset:${source.datasetId}` : `folder:${source.folder}`;
}

export function useSessionImages(
  source: ImageSource | null,
  describe: (cause: unknown, fallback: string) => string,
): SessionImages {
  const [images, setImages] = useState<readonly string[]>([]);
  const [existing, setExisting] = useState<ReadonlyMap<string, readonly CanvasBox[]>>(
    new Map(),
  );
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const key = keyOf(source);

  useEffect(() => {
    if (source === null) return;
    const controller = new AbortController();
    const noun = source.kind === 'dataset' ? 'dataset' : 'folder';

    void (async () => {
      try {
        let found: readonly string[];
        let boxes: ReadonlyMap<string, readonly CanvasBox[]> = new Map();
        if (source.kind === 'dataset') {
          const entries = await listDatasetImages(source.datasetId, controller.signal);
          boxes = new Map(
            entries.map((entry) => [entry.path, storedToCanvasBoxes(entry.boxes)]),
          );
          found = entries.map((entry) => entry.path);
        } else {
          found = await listFolderImages(source.folder, controller.signal);
        }
        if (!mounted.current || controller.signal.aborted) return;
        setImages(found);
        setExisting(boxes);
        setError(found.length === 0 ? `That ${noun} has no images.` : null);
        setGeneration((current) => current + 1);
      } catch (cause) {
        if (mounted.current && !controller.signal.aborted) {
          setError(describe(cause, `Could not read that ${noun}.`));
        }
      }
    })();

    return () => controller.abort();
    // `key`, not `source`: the object identity changes on every render of the setup form,
    // and depending on it would re-list the folder continuously.
  }, [key]);

  return { images, existing, error, generation };
}
