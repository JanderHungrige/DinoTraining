/** The annotation targets and their layer rules (doc 104), loaded once per mount. */

import { useEffect, useState } from 'react';

import { listAnnotationTargets, type AnnotationTarget } from '../api/annotationTargets';

export function useAnnotationTargetList(): readonly AnnotationTarget[] {
  const [targets, setTargets] = useState<readonly AnnotationTarget[]>([]);
  useEffect(() => {
    let live = true;
    listAnnotationTargets()
      .then((found) => live && setTargets(found))
      .catch((cause: unknown) => console.warn('Annotation targets could not be loaded', cause));
    return () => {
      live = false;
    };
  }, []);
  return targets;
}
