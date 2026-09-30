/**
 * Phrases on an outline (doc 105), as pure edits of a `CanvasBox`.
 *
 * The store's rules, mirrored so the UI never offers what would be refused: a phrase
 * belongs to one class, a class name is always its own phrase, and only outlines carry
 * phrases (doc 103).
 */

import type { PhraseInfo } from '../api/phrases';
import { ENGLISH, type Translator } from '../i18n';
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
export function refusal(box: CanvasBox, phrase: PhraseInfo, { t }: Translator = ENGLISH): string {
  if (box.mask === undefined) return t('studio.phrase.needsOutline');
  if (phraseKey(phrase.class_name) !== phraseKey(box.text ?? '')) {
    const name = box.text ?? t('studio.phrase.unnamed');
    return t('studio.phrase.otherClass', { phrase: phrase.text, className: phrase.class_name, name });
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
