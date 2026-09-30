import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { classColour } from '../lib/overlayPalette';
import { AnnotationTimeline, type AnnotationTimelineProps } from './AnnotationTimeline';

const FRAMES = [[], ['signal'], ['signal'], [], ['train'], ['signal']].map((classes) => ({
  classes,
}));

function props(overrides: Partial<AnnotationTimelineProps> = {}): AnnotationTimelineProps {
  return {
    frames: FRAMES,
    classNames: ['person', 'signal', 'train'],
    index: 0,
    selected: null,
    onSelect: vi.fn(),
    onSeek: vi.fn(),
    ...overrides,
  };
}

describe('AnnotationTimeline (doc 75)', () => {
  it('draws one bar per class present, saying how often it appears', () => {
    render(<AnnotationTimeline {...props()} />);
    expect(screen.getByRole('button', { name: 'signal: on 3 of 6 frames' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'train: on 1 of 6 frames' })).toBeInTheDocument();
    // A class of the dataset that is not in this sequence gets no bar.
    expect(screen.queryByRole('button', { name: /person/ })).not.toBeInTheDocument();
  });

  it("draws each bar's segments where the class is, in the class's own colour", () => {
    render(<AnnotationTimeline {...props()} />);
    const signal = screen.getByRole('button', { name: /^signal/ });
    const segments = [...signal.querySelectorAll<HTMLElement>('.timeline__segment')];
    expect(segments.map((s) => [s.style.left, s.style.width])).toEqual([
      ['16.666666666666664%', '33.33333333333333%'],
      ['83.33333333333334%', '16.666666666666664%'],
    ]);
    // Index 1 in the dataset's classes: the same colour the boxes are drawn in.
    const { r, g, b } = classColour(1);
    expect(segments[0]!.style.background).toBe(`rgb(${r}, ${g}, ${b})`);
  });

  it('selects a class by clicking its bar, and deselects on a second click', async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { rerender } = render(<AnnotationTimeline {...props({ onSelect })} />);
    await user.click(screen.getByRole('button', { name: /^train/ }));
    expect(onSelect).toHaveBeenLastCalledWith('train');

    rerender(<AnnotationTimeline {...props({ onSelect, selected: 'train' })} />);
    expect(screen.getByRole('button', { name: /^train/ })).toHaveAttribute('aria-pressed', 'true');
    await user.click(screen.getByRole('button', { name: /^train/ }));
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it('jumps to the first, next and previous annotation of the selected class', async () => {
    const user = userEvent.setup();
    const onSeek = vi.fn();
    render(<AnnotationTimeline {...props({ selected: 'signal', index: 2, onSeek })} />);
    await user.click(screen.getByRole('button', { name: /first/i }));
    await user.click(screen.getByRole('button', { name: /next/i }));
    await user.click(screen.getByRole('button', { name: /previous/i }));
    expect(onSeek.mock.calls.map(([position]) => position)).toEqual([1, 5, 1]);
  });

  it('cannot jump before a class is chosen', () => {
    render(<AnnotationTimeline {...props()} />);
    expect(screen.getByRole('button', { name: /first/i })).toBeDisabled();
    expect(screen.getByText('Click a bar to choose a class.')).toBeInTheDocument();
  });

  it('says so when nothing is annotated', () => {
    render(<AnnotationTimeline {...props({ frames: [{ classes: [] }] })} />);
    expect(screen.getByText(/Nothing is annotated in this sequence yet/)).toBeInTheDocument();
  });
});
