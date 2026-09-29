import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ImageReview } from '../lib/generatorSave';
import { useAutoPropose, type AutoProposeTarget } from './useAutoPropose';

const SAVED: ImageReview = {
  path: '/photos/a.png',
  boxes: [],
  masks: [],
  maskResponse: null,
  imageSize: { width: 1, height: 1 },
};

function target(overrides: Partial<AutoProposeTarget> = {}): AutoProposeTarget {
  return {
    currentImage: '/photos/a.png',
    proposing: false,
    propose: vi.fn().mockResolvedValue(null),
    saved: () => undefined,
    proposedFor: null,
    ...overrides,
  };
}

describe('useAutoPropose (doc 70)', () => {
  it('proposes once when an image arrives', () => {
    const session = target();
    const { rerender } = renderHook(({ s }) => useAutoPropose(s, true), {
      initialProps: { s: session },
    });
    rerender({ s: { ...session } });
    expect(session.propose).toHaveBeenCalledTimes(1);
  });

  it('proposes again for the next image', () => {
    const session = target();
    const { rerender } = renderHook(({ s }) => useAutoPropose(s, true), {
      initialProps: { s: session },
    });
    rerender({ s: { ...session, currentImage: '/photos/b.png' } });
    expect(session.propose).toHaveBeenCalledTimes(2);
  });

  it('does nothing when switched off', () => {
    const session = target();
    renderHook(() => useAutoPropose(session, false));
    expect(session.propose).not.toHaveBeenCalled();
  });

  it('never re-proposes an image this session saved — that would overwrite corrections', () => {
    const session = target({ saved: (path) => (path === SAVED.path ? SAVED : undefined) });
    renderHook(() => useAutoPropose(session, true));
    expect(session.propose).not.toHaveBeenCalled();
  });

  it('waits while a proposal is running, and does not retry a finished one', () => {
    const session = target({ proposing: true });
    const { rerender } = renderHook(({ s }) => useAutoPropose(s, true), {
      initialProps: { s: session },
    });
    expect(session.propose).not.toHaveBeenCalled();

    // The run ends (successfully or not) on the same image: asked for once, and only once.
    rerender({ s: { ...session, proposing: false } });
    rerender({ s: { ...session, proposing: true } });
    rerender({ s: { ...session, proposing: false } });
    expect(session.propose).toHaveBeenCalledTimes(1);
  });

  it('leaves an image alone that already has a proposal on screen (doc 71)', () => {
    // Autoplay stopped during its hold: the proposal on screen is the one the user stopped
    // to correct. Re-proposing would replace it with a fresh copy of the same mistake.
    const session = target({ proposedFor: '/photos/a.png' });
    renderHook(() => useAutoPropose(session, true));
    expect(session.propose).not.toHaveBeenCalled();
  });
});

