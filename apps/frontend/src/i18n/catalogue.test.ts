/**
 * The German catalogue is complete and actually German (doc 111). Completeness is also a
 * compile error; this test is what catches a German value left in English.
 */

import { describe, expect, it } from 'vitest';

import { de, en } from './catalogue';

/** Values that are the same in both languages on purpose: names, units, symbols. */
export const SAME_IN_BOTH = new Set<string>([
  'English',
  'Deutsch',
  'DinoTraining',
  'OK',
  'Grounding DINO',
  'Grounded SAM',
  'RF-DETR',
  'SAM 2',
  'SAM 3',
  'DINOv2',
  'DINOv3',
  'MCP',
  'COCO',
  'Admin',
  'Library',
  'Batch',
  'Backbone',
  'Head',
  'Start',
  'Stop',
  'Name',
  'Details',
  // Kept as they are in German by the glossary.
  'Annotation Studio',
  'Training',
  'Test',
  'Prompt',
]);

describe('the German catalogue', () => {
  it('has every English key and no other', () => {
    expect(Object.keys(de).sort()).toEqual(Object.keys(en).sort());
  });

  it('translates every text, apart from names that stay as they are', () => {
    const untranslated = (Object.keys(en) as (keyof typeof en)[]).filter(
      (key) => de[key] === en[key] && !SAME_IN_BOTH.has(en[key]) && /[a-z]{3}/i.test(en[key]),
    );
    expect(untranslated).toEqual([]);
  });

  it('keeps every placeholder', () => {
    const lost = (Object.keys(en) as (keyof typeof en)[]).filter((key) => {
      const wanted = (en[key].match(/\{\w+\}/g) ?? []).sort().join();
      return (de[key].match(/\{\w+\}/g) ?? []).sort().join() !== wanted;
    });
    expect(lost).toEqual([]);
  });
});
