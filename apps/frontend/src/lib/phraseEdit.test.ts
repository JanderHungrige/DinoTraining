import { describe, expect, it } from 'vitest';

import type { PhraseInfo } from '../api/phrases';
import type { CanvasBox } from '../types/annotation';
import { phraseKey, phrasesOf, refusal, withoutPhrase, withPhrase } from './phraseEdit';

const MASK = { rle: { size: [1, 1] as [number, number], counts: [0, 1] }, png: '' };
const outline = (text: string, phrases?: string[]): CanvasBox => ({
  id: 'b', label: 'positive', provenance: 'sam3', x: 0, y: 0, w: 1, h: 1, text, mask: MASK, ...(phrases ? { phrases } : {}),
});
const phrase = (text: string, className: string): PhraseInfo => ({
  id: 1, text, class_name: className, variants: [], confusable: [], instances: 0, complete: 0, absent: 0,
});

describe('phraseEdit (doc 105)', () => {
  it('keys a phrase like the store does', () => {
    expect(phraseKey('  Red   Car. ')).toBe('red car');
    expect(phraseKey('')).toBe('object');
  });

  it('an outline always answers to its class first', () => {
    expect(phrasesOf(outline('Car'))).toEqual(['car']);
    expect(phrasesOf(outline('car', ['car', 'red car']))).toEqual(['car', 'red car']);
  });

  it('adds and removes phrases, never the class, and drops an empty list', () => {
    const added = withPhrase(outline('car'), 'Red car');
    expect(added.phrases).toEqual(['car', 'red car']);
    expect(withPhrase(added, 'red car')).toBe(added);
    const removed = withoutPhrase(added, 'red car');
    expect(removed.phrases).toBeUndefined();
    expect(withoutPhrase(added, 'car').phrases).toEqual(['car', 'red car']);
  });

  it('refuses what the store would refuse, in words', () => {
    expect(refusal(outline('car'), phrase('red light', 'signal'))).toMatch(/phrase of class signal/);
    const box = { ...outline('car') };
    delete (box as { mask?: unknown }).mask;
    expect(refusal(box, phrase('red car', 'car'))).toMatch(/make one from this box first/);
    expect(refusal(outline('Car'), phrase('red car', 'car'))).toBe('');
  });
});
