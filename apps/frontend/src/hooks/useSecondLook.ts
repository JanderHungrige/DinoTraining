/**
 * A second look (doc 109): a random sample of annotated pictures shown again, each judged
 * "looks right" or "needed a change", and the share that needed one.
 */

import { useCallback, useEffect, useState } from 'react';

import { getSecondLook, recordVerdict, startSecondLook, type SecondLookInfo, type SecondLookVerdict } from '../api/quality';

export interface SecondLook {
  readonly info: SecondLookInfo | null;
  readonly active: boolean;
  readonly error: string;
  readonly start: () => void;
  readonly stop: () => void;
  readonly judge: (path: string, verdict: SecondLookVerdict) => void;
}

export function useSecondLook(datasetId: string, onFilter: (paths: readonly string[] | null) => void): SecondLook {
  const [info, setInfo] = useState<SecondLookInfo | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setInfo(null);
    if (!datasetId) return;
    let live = true;
    // A dataset that never had one answers 404: "none yet", not a failure.
    getSecondLook(datasetId)
      .then((found) => live && setInfo(found))
      .catch(() => live && setInfo(null));
    return () => {
      live = false;
    };
  }, [datasetId]);

  const fail = (cause: unknown): void => setError(cause instanceof Error ? cause.message : String(cause));

  const start = useCallback(() => {
    startSecondLook(datasetId)
      .then((found) => {
        setInfo(found);
        setActive(true);
        setError('');
        onFilter(found.sample);
      })
      .catch(fail);
  }, [datasetId, onFilter]);

  const stop = useCallback(() => {
    setActive(false);
    onFilter(null);
  }, [onFilter]);

  const judge = useCallback(
    (path: string, verdict: SecondLookVerdict) => {
      recordVerdict(datasetId, path, verdict).then(setInfo).catch(fail);
    },
    [datasetId],
  );

  return { info, active, error, start, stop, judge };
}
