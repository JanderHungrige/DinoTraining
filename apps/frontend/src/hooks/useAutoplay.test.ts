import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { GeneratorSession } from '../types/generatorSession';
import type { GeneratorConfig } from '../types/generatorConfig';
import { useAutoplay } from './useAutoplay';

vi.mock('../lib/generatorProposal', () => ({
  proposeReview: vi.fn(() => new Promise(() => undefined)),
}));

const CONFIG: GeneratorConfig = {
  kind: 'foundation',
  datasetId: 'd1',
  images: { kind: 'folder', folder: '/f' },
  foundationId: 'rf-detr-nano',
  concept: '',
  scoreThreshold: 0.3,
};

function session(): GeneratorSession {
  return {
    images: ['/f/0.png', '/f/1.png', '/f/2.png'],
    index: 1,
    goTo: vi.fn(),
    show: vi.fn(),
    save: vi.fn(),
    saved: () => undefined,
  } as unknown as GeneratorSession;
}

describe('useAutoplay (doc 71)', () => {
  it('knows the run length before the first image is done', () => {
    const { result } = renderHook(() => useAutoplay(CONFIG, session()));
    act(() => result.current.play());
    expect(result.current.running).toBe(true);
    // From image 1 of three: two to go. Never "0 of 0" while the first one is proposing.
    expect(result.current.progress).toMatchObject({ done: 0, total: 2 });
  });

  it('remembers the hidden choice (doc 69)', () => {
    const first = renderHook(() => useAutoplay(CONFIG, session()));
    act(() => first.result.current.setHidden(true));
    first.unmount();
    const second = renderHook(() => useAutoplay(CONFIG, session()));
    expect(second.result.current.hidden).toBe(true);
  });

  it('does nothing without a config', () => {
    const { result } = renderHook(() => useAutoplay(null, session()));
    act(() => result.current.play());
    expect(result.current.running).toBe(false);
  });
});
