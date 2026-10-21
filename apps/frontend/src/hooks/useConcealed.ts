/**
 * What the Studio keeps off screen (split out of the Studio at the 300-line gate, doc 170).
 *
 * Two reasons a box is not drawn, kept apart on purpose. `belowCutoff` is what the
 * slider is filtering and what `Remove N below` discards; `hidden` is everything not on
 * screen. Folding them together would make the remove button delete boxes the user only
 * asked to get out of the way — the worst thing this screen can do.
 *
 * `concealed` is a **snapshot of what was there when "hide" was pressed**, not a live
 * predicate: a box drawn afterwards is the whole point of pressing it, and a rule like
 * "hide everything not hand-drawn" would hide the new one the moment it was saved and
 * reloaded. Null means nothing is concealed. It does not survive moving to the next
 * picture — the ids would be stale anyway.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';

import { hiddenByThreshold } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';

export interface Concealed {
  readonly belowCutoff: ReadonlySet<string>;
  readonly hidden: ReadonlySet<string>;
  readonly concealed: ReadonlySet<string> | null;
  /** Get everything currently on screen out of the way, or bring it all back. */
  readonly toggle: () => void;
}

export function useConcealed(boxes: readonly CanvasBox[], threshold: number, currentImage: string | null): Concealed {
  const [concealed, setConcealed] = useState<ReadonlySet<string> | null>(null);
  const belowCutoff = useMemo(() => hiddenByThreshold(boxes, threshold), [boxes, threshold]);
  const hidden = useMemo(() => {
    if (concealed === null) return belowCutoff;
    const all = new Set(belowCutoff);
    for (const id of concealed) all.add(id);
    return all;
  }, [belowCutoff, concealed]);
  useEffect(() => setConcealed(null), [currentImage]);
  const toggle = useCallback((): void => {
    setConcealed((current) => (current === null ? new Set(boxes.map((box) => box.id)) : null));
  }, [boxes]);
  return { belowCutoff, hidden, concealed, toggle };
}
