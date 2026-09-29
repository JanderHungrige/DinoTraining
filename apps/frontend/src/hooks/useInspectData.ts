/**
 * What the Inspect tab shows for one dataset (doc 74): its sequences, complete and in
 * order, and the boxes stored on each image.
 *
 * Two requests, not one: the sequences route answers "which frames, in which order, with
 * which classes" (also what doc 75's timeline draws), and the long-standing image listing
 * already carries every stored box. Masks are fetched per frame, on demand, because they
 * are ~13 KB each and a sequence can have hundreds.
 */

import { useEffect, useState } from 'react';

import { listDatasetImages, type DatasetImageInfo } from '../api/datasets';
import { listDatasetSequences, type DatasetSequences } from '../api/datasetSequences';

export interface InspectData {
  readonly sequences: DatasetSequences | null;
  /** Stored image path -> its listing entry (size and boxes). */
  readonly images: ReadonlyMap<string, DatasetImageInfo>;
  readonly loading: boolean;
  readonly error: string | null;
}

const EMPTY: ReadonlyMap<string, DatasetImageInfo> = new Map();

export function useInspectData(datasetId: string): InspectData {
  const [sequences, setSequences] = useState<DatasetSequences | null>(null);
  const [images, setImages] = useState<ReadonlyMap<string, DatasetImageInfo>>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Cleared before loading, so one dataset's frames never play under another's name.
    setSequences(null);
    setImages(EMPTY);
    setError(null);
    if (!datasetId) return;
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      listDatasetSequences(datasetId, controller.signal),
      listDatasetImages(datasetId, controller.signal),
    ])
      .then(([found, listing]) => {
        setSequences(found);
        setImages(new Map(listing.map((entry) => [entry.path, entry])));
      })
      .catch((caught: unknown) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : 'Could not load that dataset.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [datasetId]);

  return { sequences, images, loading, error };
}
