import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { AnnotationSession } from '../hooks/useAnnotationSession';
import type { CanvasBox } from '../types/annotation';
import { StudioActions } from './StudioActions';

const BOX: CanvasBox = { id: 'b1', label: 'positive', provenance: 'hand-drawn', x: 0, y: 0, w: 1, h: 1, text: 'car' };

function session(overrides: Partial<AnnotationSession> = {}): AnnotationSession {
  return {
    images: ['/a.png', '/b.png'], loadingImages: false, allImages: ['/a.png', '/b.png'], filtered: false,
    setFilter: vi.fn(), index: 0, currentImage: '/a.png', boxes: [], imageSize: null,
    counts: { images: 2, annotated: 0, boxes: 0 } as unknown as AnnotationSession['counts'],
    dirty: false, busy: false, proposing: false, error: null, setBoxes: vi.fn(), reportImageSize: vi.fn(),
    propose: vi.fn(async () => undefined), save: vi.fn(async () => true), next: vi.fn(async () => undefined),
    previous: vi.fn(async () => undefined), canGoNext: true, canGoPrevious: false, ...overrides,
  };
}

beforeEach(() => localStorage.clear());

describe('StudioActions (the Generator bar, Jan 2026-09-30)', () => {
  it('puts Run and Save beside Previous and Next, with the automation named below', () => {
    render(<StudioActions session={session()} runLabel="Run prompt" />);
    const bar = screen.getByRole('toolbar');
    expect([...bar.querySelectorAll('button')].map((b) => b.textContent)).toEqual(['Run prompt', 'Save to dataset', '← Previous', 'Next →']);
    expect(screen.getByRole('checkbox', { name: /Auto-propose/ })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Auto-save/ })).toBeChecked();
  });

  it('Auto-propose runs once on a picture with nothing on it, never over existing boxes', async () => {
    const user = userEvent.setup();
    const empty = session();
    const { rerender } = render(<StudioActions session={empty} runLabel="Run prompt" />);
    await user.click(screen.getByRole('checkbox', { name: /Auto-propose/ }));
    expect(empty.propose).toHaveBeenCalledOnce();
    const annotated = session({ currentImage: '/b.png', boxes: [BOX] });
    rerender(<StudioActions session={annotated} runLabel="Run prompt" />);
    expect(annotated.propose).not.toHaveBeenCalled();
  });

  it('with Auto-save off, moving on from unsaved changes is refused rather than dropping them', async () => {
    const user = userEvent.setup();
    const dirty = session({ dirty: true });
    render(<StudioActions session={dirty} runLabel="Run prompt" />);
    await user.click(screen.getByRole('checkbox', { name: /Auto-save/ }));
    await user.click(screen.getByRole('button', { name: 'Next →' }));
    expect(dirty.next).not.toHaveBeenCalled();
    expect(screen.getByRole('alert')).toHaveTextContent('Save first, or turn Auto-save on.');
  });

  it('with Auto-save on, Next moves on (the session saves first)', async () => {
    const user = userEvent.setup();
    const dirty = session({ dirty: true });
    render(<StudioActions session={dirty} runLabel="Run prompt" />);
    await user.click(screen.getByRole('button', { name: 'Next →' }));
    expect(dirty.next).toHaveBeenCalledOnce();
  });

  it('in a review proposes only that class, even over existing annotations (doc 119)', async () => {
    const user = userEvent.setup();
    const reviewing = session({ boxes: [BOX] });
    render(<StudioActions session={reviewing} runLabel="Run prompt" only="m10" />);
    await user.click(screen.getByRole('button', { name: 'Run prompt' }));
    expect(reviewing.propose).toHaveBeenCalledWith('m10');
    await user.click(screen.getByRole('checkbox', { name: /Auto-propose/ }));
    expect(reviewing.propose).toHaveBeenCalledTimes(2);
  });
});
