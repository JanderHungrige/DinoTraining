/**
 * Keys for the phrase bar (doc 105): 1–9 pick the active phrase, A marks the picture
 * "all marked" and N "not in this picture" for it. Never while typing in a field.
 *
 * A focused box on the canvas owns 1/2/3 and N (its verdict) and marks those keys handled;
 * a handled key is left alone here, so the box wins and nothing happens twice.
 */

import { useEffect } from 'react';

function typing(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}

export function usePhraseKeys(
  enabled: boolean,
  count: number,
  onPick: (index: number) => void,
  onMark: (status: 'complete' | 'absent') => void,
): void {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent): void => {
      if (event.defaultPrevented || typing(event.target)) return;
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const digit = Number(event.key);
      if (Number.isInteger(digit) && digit >= 1 && digit <= Math.min(9, count)) {
        onPick(digit - 1);
      } else if (event.key === 'a' || event.key === 'A') {
        onMark('complete');
      } else if (event.key === 'n' || event.key === 'N') {
        onMark('absent');
      } else {
        return;
      }
      event.preventDefault();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [enabled, count, onPick, onMark]);
}
