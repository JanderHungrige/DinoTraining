import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  isImageSource,
  isNumber,
  isOneOf,
  isShapeOf,
  isString,
  isStringArray,
  readPersisted,
  stillListed,
  storageKeyFor,
  writePersisted,
} from './persisted';

describe('storage keys', () => {
  it('namespaces and versions every key', () => {
    expect(storageKeyFor('generator.concept')).toBe('dinotraining.v1.generator.concept');
  });
});

describe('readPersisted / writePersisted', () => {
  afterEach(() => vi.restoreAllMocks());

  it('round-trips a value through localStorage as JSON', () => {
    writePersisted('a', { kind: 'folder', folder: '/data/rail' });
    expect(localStorage.getItem('dinotraining.v1.a')).toBe('{"kind":"folder","folder":"/data/rail"}');
    expect(readPersisted('a', { kind: 'folder', folder: '' }, isImageSource)).toEqual({
      kind: 'folder',
      folder: '/data/rail',
    });
  });

  it('returns the fallback when nothing is stored', () => {
    expect(readPersisted('missing', 'dflt', isString)).toBe('dflt');
  });

  it('returns the fallback when the stored value fails its guard', () => {
    localStorage.setItem('dinotraining.v1.n', '"not a number"');
    expect(readPersisted('n', 0.3, isNumber)).toBe(0.3);
  });

  it('returns the fallback when the stored text is not JSON', () => {
    localStorage.setItem('dinotraining.v1.broken', '{truncated');
    expect(readPersisted('broken', 'dflt', isString)).toBe('dflt');
  });

  it('falls back instead of throwing when storage itself throws', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError');
    });
    expect(readPersisted('k', 'dflt', isString)).toBe('dflt');
    expect(() => writePersisted('k', 'value')).not.toThrow();
    expect(warn).toHaveBeenCalled();
    expect(String(warn.mock.calls[0]?.[0])).toContain('k');
  });
});

describe('guards', () => {
  it('isNumber rejects NaN and infinities, which JSON cannot carry faithfully', () => {
    expect(isNumber(0.25)).toBe(true);
    expect(isNumber(Number.NaN)).toBe(false);
    expect(isNumber('0.25')).toBe(false);
  });

  it('isOneOf accepts only listed literals', () => {
    const mode = isOneOf(['expert', 'masks', 'foundation'] as const);
    expect(mode('masks')).toBe(true);
    expect(mode('prompt')).toBe(false);
  });

  it('isStringArray rejects mixed arrays', () => {
    expect(isStringArray(['a', 'b'])).toBe(true);
    expect(isStringArray(['a', 1])).toBe(false);
    expect(isStringArray('a')).toBe(false);
  });

  it('isImageSource checks both kinds and their fields', () => {
    expect(isImageSource({ kind: 'dataset', datasetId: 'd1' })).toBe(true);
    expect(isImageSource({ kind: 'dataset', folder: '/x' })).toBe(false);
    // A video needs its range too (doc 73); a half-remembered one falls back whole.
    expect(isImageSource({ kind: 'video', path: '/x' })).toBe(false);
    expect(
      isImageSource({ kind: 'video', path: '/v.mp4', range: { start: 0, count: 60, stride: 2 } }),
    ).toBe(true);
    expect(isImageSource({ kind: 'photo', path: '/x' })).toBe(false);
  });

  it('isShapeOf needs every default key with the same type, and arrays to stay arrays', () => {
    const defaults = { datasetIds: [] as string[], backboneId: '', epochs: 20 };
    const guard = isShapeOf(defaults);
    expect(guard({ datasetIds: ['d'], backboneId: 'b', epochs: 5 })).toBe(true);
    expect(guard({ datasetIds: ['d'], backboneId: 'b' })).toBe(false);
    expect(guard({ datasetIds: 'd', backboneId: 'b', epochs: 5 })).toBe(false);
    expect(guard({ datasetIds: [], backboneId: 'b', epochs: '5' })).toBe(false);
    expect(guard(null)).toBe(false);
  });
});

describe('stillListed', () => {
  it('keeps an id that is still offered', () => {
    expect(stillListed('d2', ['d1', 'd2'])).toBe('d2');
  });

  it('drops an id that is no longer offered, so the caller falls back to the first', () => {
    expect(stillListed('deleted', ['d1', 'd2'])).toBe('');
  });

  it('drops everything while the list is still loading', () => {
    expect(stillListed('d2', [])).toBe('');
  });
});
