import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { vi } from 'vitest';

import { usePlayback } from './usePlayback';

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe('usePlayback (doc 74)', () => {
  it('advances at the rate asked for and stops at the last frame', () => {
    const { result } = renderHook(() => usePlayback(3, 5, 'a'));
    act(() => result.current.toggle());
    act(() => void vi.advanceTimersByTime(200));
    expect(result.current.index).toBe(1);
    act(() => void vi.advanceTimersByTime(1000));
    expect(result.current.index).toBe(2);
    expect(result.current.playing).toBe(false);
  });

  it('plays from the start again once the end was reached', () => {
    const { result } = renderHook(() => usePlayback(3, 5, 'a'));
    act(() => result.current.setIndex(2));
    act(() => result.current.toggle());
    expect(result.current.index).toBe(0);
    expect(result.current.playing).toBe(true);
  });

  it('stepping pauses, and never leaves the track', () => {
    const { result } = renderHook(() => usePlayback(3, 5, 'a'));
    act(() => result.current.toggle());
    act(() => result.current.step(-1));
    expect(result.current.playing).toBe(false);
    expect(result.current.index).toBe(0);
    act(() => result.current.step(10));
    expect(result.current.index).toBe(2);
  });

  it('a new track starts at its beginning, paused', () => {
    const { result, rerender } = renderHook(({ key }) => usePlayback(10, 5, key), {
      initialProps: { key: 'a' },
    });
    act(() => result.current.setIndex(7));
    act(() => result.current.toggle());
    rerender({ key: 'b' });
    expect(result.current.index).toBe(0);
    expect(result.current.playing).toBe(false);
  });
});
