import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ParameterSetInfo } from '../api/parameters';
import { finetuneFields, useParameters } from './useParameters';

vi.mock('../api/parameters', async () => {
  const actual = await vi.importActual<typeof import('../api/parameters')>('../api/parameters');
  return { ...actual, getParameters: vi.fn() };
});
const api = await import('../api/parameters');

function set(family: string, keys: Record<string, number>): ParameterSetInfo {
  return {
    family, title: family, covers: '',
    parameters: Object.entries(keys).map(([key, value]) => ({
      key, label: key, term: key, help: 'h', default: value, why: 'w', kind: 'float', level: 'basic',
      minimum: 0, maximum: 100, choices: [], recipe_overrides: false,
    })),
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(api.getParameters).mockImplementation(async (id: string) =>
    id === 'sam3' ? set('sam3', { epochs: 4, learning_rate: 1e-4 }) : set('sam2', { epochs: 6, box_jitter: 0.1 }),
  );
});

describe('useParameters (doc 100)', () => {
  it('has no values before the catalogue arrives, then the defaults — never a seeded guess', async () => {
    // CLAUDE.md's sequence: render before the load, then after it.
    const { result } = renderHook(({ id }) => useParameters(id), { initialProps: { id: 'sam2.1-hiera-small' } });
    expect(result.current.values).toEqual({});
    await waitFor(() => expect(result.current.values).toEqual({ epochs: 6, box_jitter: 0.1 }));
  });

  it('keeps each family its own changes', async () => {
    const { result, rerender } = renderHook(({ id }) => useParameters(id), { initialProps: { id: 'sam2.1-hiera-small' } });
    await waitFor(() => expect(result.current.set?.family).toBe('sam2'));
    result.current.change('epochs', 9);
    await waitFor(() => expect(result.current.values['epochs']).toBe(9));
    rerender({ id: 'sam3' });
    await waitFor(() => expect(result.current.set?.family).toBe('sam3'));
    expect(result.current.values['epochs']).toBe(4);
    rerender({ id: 'sam2.1-hiera-small' });
    await waitFor(() => expect(result.current.values['epochs']).toBe(9));
  });

  it('does not show the previous model\'s settings while the next one loads', async () => {
    const { result, rerender } = renderHook(({ id }) => useParameters(id), { initialProps: { id: 'sam2.1-hiera-small' } });
    await waitFor(() => expect(result.current.set?.family).toBe('sam2'));
    let release: (value: ParameterSetInfo) => void = () => undefined;
    vi.mocked(api.getParameters).mockImplementationOnce(() => new Promise((resolve) => { release = resolve; }));
    rerender({ id: 'sam3' });
    expect(result.current.set).toBeNull();
    release(set('sam3', { epochs: 4 }));
    await waitFor(() => expect(result.current.set?.family).toBe('sam3'));
  });

  it('setting a value back to its default removes the override', async () => {
    const { result } = renderHook(() => useParameters('sam2.1-hiera-small'));
    await waitFor(() => expect(result.current.set).not.toBeNull());
    result.current.change('box_jitter', 0.3);
    await waitFor(() => expect(result.current.overrides).toEqual({ box_jitter: 0.3 }));
    result.current.change('box_jitter', 0.1);
    await waitFor(() => expect(result.current.overrides).toEqual({}));
  });
});

describe('finetuneFields', () => {
  it('names rounds, learning speed and seed, and sends the rest as options', () => {
    expect(finetuneFields({ epochs: 6, learning_rate: 1e-4, seed: 42, box_jitter: 0.2, flag: true })).toEqual({
      epochs: 6, learning_rate: 1e-4, seed: 42, options: { box_jitter: 0.2, flag: 1 },
    });
  });
});
