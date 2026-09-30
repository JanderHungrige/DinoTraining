/**
 * The annotation target chosen in the Studio's setup (doc 104): the backend's list, the
 * user's remembered choice, and what Start records.
 */

import { useCallback } from 'react';

import { saveDatasetTarget, type AnnotationTarget } from '../api/annotationTargets';
import { useAnnotationTargetList } from './useAnnotationTargetList';
import { usePersistentState } from './usePersistentState';
import { isString, stillListed, writePersisted } from '../lib/persisted';

export const DEFAULT_TARGET = 'open';

export interface AnnotationTargets {
  readonly targets: readonly AnnotationTarget[];
  readonly target: string;
  readonly setTarget: (target: string) => void;
  /** Store the choice with the dataset, and point Prepare data at its model. */
  readonly commit: (datasetId: string) => void;
}

export function useAnnotationTargets(): AnnotationTargets {
  const targets = useAnnotationTargetList();
  const [choice, setTarget] = usePersistentState('studio.target', DEFAULT_TARGET, isString);
  const target = stillListed(choice, targets.map((t) => t.id)) || DEFAULT_TARGET;

  const commit = useCallback(
    (datasetId: string) => {
      const profile = targets.find((t) => t.id === target)?.profile;
      // Prepare data opens at what it remembers (doc 69).
      if (profile) writePersisted('prepare.target', profile);
      saveDatasetTarget(datasetId, target).catch((cause: unknown) =>
        console.warn(`Could not record the annotation target for ${datasetId}`, cause),
      );
    },
    [targets, target],
  );

  return { targets, target, setTarget, commit };
}
