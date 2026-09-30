/**
 * A dataset's phrases and one picture's phrase statuses (docs 103–105), loaded — never
 * seeded — and refreshed after a change.
 */

import { useCallback, useEffect, useState } from 'react';

import {
  listPhrases,
  pictureStatuses,
  setPictureStatus,
  type PhraseInfo,
  type PhraseStatus,
  type PictureStatus,
} from '../api/phrases';

export interface PicturePhrases {
  readonly phrases: readonly PhraseInfo[];
  readonly statuses: readonly PictureStatus[];
  readonly error: string;
  readonly reload: () => void;
  readonly mark: (phrase: string, status: PhraseStatus | null) => Promise<void>;
}

function message(cause: unknown): string {
  return cause instanceof Error ? cause.message : String(cause);
}

export function usePicturePhrases(datasetId: string | null, path: string | null): PicturePhrases {
  const [phrases, setPhrases] = useState<readonly PhraseInfo[]>([]);
  const [statuses, setStatuses] = useState<readonly PictureStatus[]>([]);
  const [error, setError] = useState('');
  const [generation, setGeneration] = useState(0);
  const reload = useCallback(() => setGeneration((n) => n + 1), []);

  useEffect(() => {
    if (!datasetId) return;
    let live = true;
    listPhrases(datasetId)
      .then((found) => live && setPhrases(found))
      .catch((cause: unknown) => live && setError(message(cause)));
    return () => {
      live = false;
    };
  }, [datasetId, generation]);

  useEffect(() => {
    setStatuses([]);
    if (!datasetId || !path) return;
    let live = true;
    // A picture never saved has no row yet, and no statuses: a 404 here is the ordinary case.
    pictureStatuses(datasetId, path)
      .then((found) => live && setStatuses(found))
      .catch(() => live && setStatuses([]));
    return () => {
      live = false;
    };
  }, [datasetId, path, generation]);

  const mark = useCallback(
    async (phrase: string, status: PhraseStatus | null) => {
      if (!datasetId || !path) return;
      try {
        setStatuses(await setPictureStatus(datasetId, path, phrase, status));
        setError('');
        reload();
      } catch (cause) {
        setError(message(cause));
      }
    },
    [datasetId, path, reload],
  );

  return { phrases, statuses, error, reload, mark };
}
