import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { isNumber, isString } from '../lib/persisted';
import { usePersistentState } from './usePersistentState';

describe('usePersistentState', () => {
  it('starts from the default when nothing is remembered', () => {
    const { result } = renderHook(() => usePersistentState('t.name', '', isString));
    expect(result.current[0]).toBe('');
  });

  it('survives an unmount — which is what a tab switch is', () => {
    const first = renderHook(() => usePersistentState('t.folder', '', isString));
    act(() => first.result.current[1]('/data/rail'));
    expect(first.result.current[0]).toBe('/data/rail');
    first.unmount();

    const second = renderHook(() => usePersistentState('t.folder', '', isString));
    expect(second.result.current[0]).toBe('/data/rail');
  });

  it('accepts an updater function, like useState', () => {
    const { result } = renderHook(() => usePersistentState('t.count', 1, isNumber));
    act(() => result.current[1]((n) => n + 1));
    act(() => result.current[1]((n) => n + 1));
    expect(result.current[0]).toBe(3);
    expect(localStorage.getItem('dinotraining.v1.t.count')).toBe('3');
  });

  it('keeps two keys apart', () => {
    const a = renderHook(() => usePersistentState('studio.prescan.labels', '', isString));
    const b = renderHook(() => usePersistentState('generator.prescan.labels', '', isString));
    act(() => a.result.current[1]('signal'));
    expect(b.result.current[0]).toBe('');
  });

  it('ignores a stored value that fails the guard', () => {
    localStorage.setItem('dinotraining.v1.t.threshold', '"high"');
    const { result } = renderHook(() => usePersistentState('t.threshold', 0.3, isNumber));
    expect(result.current[0]).toBe(0.3);
  });
});
