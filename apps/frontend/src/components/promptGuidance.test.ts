/**
 * Prompt guidance (doc 39).
 *
 * By Wave 7 "the prompt" is three different things and which one you are looking at is not
 * visible from the field. These tests are about the guidance saying the right thing for the
 * mode — especially the head case, where the honest answer to a missing field is not
 * "there is no prompt" but "here is what it will look for instead".
 */

import { describe, expect, it } from 'vitest';

import { GROUNDING_DINO_HINT, headModeHint } from './promptGuidance';

describe('the Grounding DINO hint', () => {
  it('shows the single-label form', () => {
    expect(GROUNDING_DINO_HINT).toContain('“a bolt”');
  });

  it('shows the several-labels form, which is the part nobody guesses', () => {
    // Full stops as separators is the whole trick, and an empty field with a placeholder
    // is not enough to convey it.
    expect(GROUNDING_DINO_HINT).toContain('a bolt. a nut. a washer.');
  });

  it('warns that it finds things you did not ask for', () => {
    // Open-vocabulary detection over-proposes by design. Someone who is not told reads
    // the extra boxes as the app being broken rather than as work to reject.
    expect(GROUNDING_DINO_HINT).toMatch(/did not ask for|reject/i);
  });
});

describe('the head-mode hint', () => {
  it('names the classes the head will actually propose', () => {
    const hint = headModeHint(['bolt', 'nut']);
    expect(hint).toContain('bolt');
    expect(hint).toContain('nut');
  });

  it('says why there is no prompt rather than only that there is none', () => {
    expect(headModeHint(['bolt'])).toMatch(/takes an image/);
  });

  it('summarises a long class list instead of printing all of it', () => {
    // The chess head has thirteen. Listing them all turns a hint into a wall.
    const classes = Array.from({ length: 13 }, (_, index) => `piece-${index}`);
    const hint = headModeHint(classes);

    expect(hint).toContain('and 9 more');
    expect(hint).not.toContain('piece-12');
  });

  it('lists a short class list in full', () => {
    const hint = headModeHint(['dog', 'person']);
    expect(hint).toContain('dog, person');
    expect(hint).not.toContain('more');
  });

  it('still says something useful when the head has no class names', () => {
    // Pretrained defaults can arrive with an empty `class_names`. A hint that renders
    // "trained to find " with nothing after it is worse than a general sentence.
    const hint = headModeHint([]);
    expect(hint.length).toBeGreaterThan(40);
    expect(hint).not.toMatch(/find\s*\./);
  });
});
