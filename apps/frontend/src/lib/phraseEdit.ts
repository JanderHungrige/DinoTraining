/**
 * Phrases on an outline (doc 105), as pure edits of a `CanvasBox`.
 *
 * The store's rules, mirrored so the UI never offers what would be refused: a phrase
 * belongs to one class, a class name is always its own phrase, and only outlines carry
 * phrases (doc 103).
 */

import type { PhraseInfo } from '../api/phrases';
import type { CanvasBox } from '../types/annotation';

/** As the backend stores a phrase: lower case, spaces collapsed, a trailing stop dropped. */
export function phraseKey(text: string): string {
  const key = text.trim().toLowerCase().replace(/\.+$/, '').split(/\s+/).filter(Boolean).join(' ');
  return key || 'object';
}

export function phrasesOf(box: CanvasBox): readonly string[] {
  const own = phraseKey(box.text ?? '');
  const rest = (box.phrases ?? []).filter((p) => p !== own);
  return [own, ...rest];
}

/** Why `phrase` cannot go on `box`, or '' when it can. */
export function refusal(box: CanvasBox, phrase: PhraseInfo): string {
  if (box.mask === undefined) return 'Phrases go on outlines — make one from this box first.';
  if (phraseKey(phrase.class_name) !== phraseKey(box.text ?? '')) {
    return `"${phrase.text}" is a phrase of class ${phrase.class_name}; this outline is ${box.text ?? 'unnamed'}.`;
  }
  return '';
}

export function withPhrase(box: CanvasBox, phrase: string): CanvasBox {
  const current = phrasesOf(box);
  const key = phraseKey(phrase);
  return current.includes(key) ? box : { ...box, phrases: [...current, key] };
}

export function withoutPhrase(box: CanvasBox, phrase: string): CanvasBox {
  const [own, ...rest] = phrasesOf(box);
  const kept = rest.filter((p) => p !== phraseKey(phrase));
  if (kept.length > 0) return { ...box, phrases: [own!, ...kept] };
  const { phrases: _dropped, ...plain } = box;
  return plain;
}
