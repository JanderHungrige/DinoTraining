import { describe, expect, it } from 'vitest';

import { phraseKey } from './phraseEdit';

describe('phraseKey (doc 103)', () => {
  it('keys a phrase like the store does', () => {
    expect(phraseKey('  Red   Car. ')).toBe('red car');
    expect(phraseKey('')).toBe('object');
  });
});
