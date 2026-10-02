/** Every dataset's parameters (doc 136), keyed by id; re-read when the list changes. */

import { useEffect, useState } from 'react';

import { listProfiles, type DatasetProfile } from '../api/datasetImport';

export function useDatasetProfiles(enabled: boolean, listKey: string): ReadonlyMap<string, DatasetProfile> {
  const [profiles, setProfiles] = useState<ReadonlyMap<string, DatasetProfile>>(new Map());
  useEffect(() => {
    if (!enabled) return undefined;
    const controller = new AbortController();
    listProfiles(controller.signal)
      .then((entries) => setProfiles(new Map(entries.map((entry) => [entry.dataset_id, entry]))))
      .catch((error: unknown) => {
        // The list still shows its counts without them; say why in the log, not the UI.
        if (!controller.signal.aborted) console.warn('Dataset profiles unavailable', error);
      });
    return () => controller.abort();
  }, [enabled, listKey]);
  return profiles;
}
