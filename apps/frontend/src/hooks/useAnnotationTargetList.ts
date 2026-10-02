/** The annotation targets and their layer rules (doc 104), loaded per mount and per language. */

import { useEffect, useState } from 'react';

import { useT } from '../i18n';

import { listAnnotationTargets, type AnnotationTarget } from '../api/annotationTargets';

export function useAnnotationTargetList(): readonly AnnotationTarget[] {
  const [targets, setTargets] = useState<readonly AnnotationTarget[]>([]);
  // The backend writes the titles in the request's language: read again when it changes,
  // or the Studio, which stays mounted, keeps the old language (2026-10-02).
  const { lang } = useT();
  useEffect(() => {
    let live = true;
    listAnnotationTargets()
      .then((found) => live && setTargets(found))
      .catch((cause: unknown) => console.warn('Annotation targets could not be loaded', cause));
    return () => {
      live = false;
    };
  }, [lang]);
  return targets;
}
