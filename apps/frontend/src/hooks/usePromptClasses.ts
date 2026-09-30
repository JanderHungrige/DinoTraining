/**
 * The prompt's terms become stored classes when a Studio session starts (doc 117).
 *
 * A picture counts as complete for the classes that existed when it was saved. Asking for
 * "m8, m9, m10" from the first picture means all three exist from then — even if m10 is
 * first found on picture 3. Without this, pictures 1–2 would count as never looked at for
 * m10: safe, but it would waste their "no m10 here".
 */

import { useEffect } from 'react';

import { createDatasetClass } from '../api/datasetClasses';
import type { SessionConfig } from './useAnnotationSession';
import { prescanSuggestions } from '../lib/prescanSource';

export function usePromptClasses(config: SessionConfig | null): void {
  useEffect(() => {
    if (config === null || config.source.kind !== 'prompt') return;
    for (const term of prescanSuggestions(config.source)) {
      // Idempotent on the backend; a failure only costs the head start, so it is logged.
      createDatasetClass(config.datasetId, term).catch((cause: unknown) =>
        console.warn(`Could not store prompt class ${term}`, cause),
      );
    }
  }, [config]);
}
